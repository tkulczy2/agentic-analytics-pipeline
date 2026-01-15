"""Data Extraction Agent for extracting healthcare data from PostgreSQL."""
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.agents.base import BaseAgent
from src.models.workflow import AgentResult, AgentStatus, WorkflowState
from src.services.database import DatabaseService
from src.services.state_manager import StateManager
from src.config import settings

logger = logging.getLogger(__name__)


class DataExtractionAgent(BaseAgent):
    """Agent for extracting healthcare data from PostgreSQL."""

    # Dataset configurations
    DATASETS = {
        "members": {
            "table": "members",
            "query": """
                SELECT
                    member_id, first_name, last_name, date_of_birth, gender,
                    attribution_start_date, attribution_end_date,
                    primary_pcp_id, pcp_name, hcc_risk_score, risk_category
                FROM members
                WHERE attribution_start_date <= :end_date
                AND (attribution_end_date IS NULL OR attribution_end_date >= :start_date)
            """,
            "incremental_field": "updated_at",
            "output_file": "members.csv"
        },
        "medical_claims": {
            "table": "medical_claims",
            "query": """
                SELECT
                    c.claim_id, c.member_id, c.service_date, c.paid_date,
                    c.paid_amount, c.allowed_amount, c.place_of_service,
                    c.provider_specialty, c.primary_diagnosis, c.claim_status,
                    c.service_category, c.er_visit, c.inpatient_admit
                FROM medical_claims c
                INNER JOIN members m ON c.member_id = m.member_id
                WHERE c.service_date BETWEEN :start_date AND :end_date
                AND m.attribution_start_date <= :end_date
            """,
            "incremental_field": "c.updated_at",
            "output_file": "medical_claims.csv"
        },
        "pharmacy_claims": {
            "table": "pharmacy_claims",
            "query": """
                SELECT
                    c.claim_id, c.member_id, c.fill_date, c.paid_amount,
                    c.drug_name, c.generic_indicator, c.days_supply,
                    c.therapeutic_class, c.condition_category
                FROM pharmacy_claims c
                INNER JOIN members m ON c.member_id = m.member_id
                WHERE c.fill_date BETWEEN :start_date AND :end_date
                AND m.attribution_start_date <= :end_date
            """,
            "incremental_field": "c.updated_at",
            "output_file": "pharmacy_claims.csv"
        },
        "quality_measures": {
            "table": "quality_measures",
            "query": """
                SELECT
                    measure_id, measure_name, measure_category,
                    numerator, denominator, exclusions,
                    performance_rate, national_benchmark, measure_weight,
                    performance_year, performance_month
                FROM quality_measures
                WHERE performance_year = :year
                AND performance_month <= :month
            """,
            "incremental_field": "updated_at",
            "output_file": "quality_measures.csv"
        }
    }

    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        database: Optional[DatabaseService] = None,
        data_dir: Optional[str] = None
    ):
        super().__init__(name="DataExtractionAgent", state_manager=state_manager)
        self.database = database or DatabaseService()
        self.data_dir = Path(data_dir or settings.data_dir) / "extracts"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def execute(self, workflow_state: WorkflowState) -> AgentResult:
        """Execute data extraction."""
        started_at = datetime.now()

        try:
            # Determine extraction mode
            last_extraction = await self.state_manager.get_last_extraction_time(
                workflow_state.contract_id
            )
            extraction_mode = self._decide_extraction_mode(last_extraction)

            await self._log(
                workflow_state.workflow_id,
                "info",
                f"Extraction mode: {extraction_mode}"
            )

            # Calculate date range
            year = workflow_state.performance_year
            month = workflow_state.performance_month

            start_date = datetime(year, 1, 1)
            end_date = datetime(year, month, 1) + timedelta(days=32)
            end_date = end_date.replace(day=1) - timedelta(days=1)  # Last day of month

            # Extract datasets in parallel
            extraction_tasks = []
            for dataset_name, config in self.DATASETS.items():
                task = self._extract_dataset(
                    workflow_state.workflow_id,
                    dataset_name,
                    config,
                    year,
                    month,
                    start_date,
                    end_date,
                    extraction_mode,
                    last_extraction
                )
                extraction_tasks.append(task)

            results = await asyncio.gather(*extraction_tasks, return_exceptions=True)

            # Process results
            extracted_files = []
            records_extracted = {}
            errors = []

            for i, result in enumerate(results):
                dataset_name = list(self.DATASETS.keys())[i]

                if isinstance(result, Exception):
                    errors.append({
                        "dataset": dataset_name,
                        "error": str(result)
                    })
                else:
                    file_path, record_count = result
                    extracted_files.append(str(file_path))
                    records_extracted[dataset_name] = record_count

            if errors:
                return self._create_failure_result(
                    started_at=started_at,
                    error_message=f"Failed to extract {len(errors)} datasets",
                    error_details={"extraction_errors": errors}
                )

            return self._create_success_result(
                started_at=started_at,
                result_data={
                    "extraction_mode": extraction_mode,
                    "extracted_files": extracted_files,
                    "records_extracted": records_extracted,
                    "date_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    }
                }
            )

        except Exception as e:
            logger.exception(f"Data extraction failed: {e}")
            return self._create_failure_result(
                started_at=started_at,
                error_message=str(e)
            )

    async def _extract_dataset(
        self,
        workflow_id: str,
        dataset_name: str,
        config: Dict[str, Any],
        year: int,
        month: int,
        start_date: datetime,
        end_date: datetime,
        extraction_mode: str,
        last_extraction: Optional[datetime]
    ) -> tuple:
        """Extract a single dataset."""
        await self._log(workflow_id, "info", f"Extracting {dataset_name}...")

        query = config["query"]

        # Add incremental filter if applicable
        if extraction_mode == "incremental" and last_extraction:
            incremental_date = last_extraction - timedelta(days=7)
            query = query.rstrip() + f" AND {config['incremental_field']} >= :incremental_date"

        params = {
            "year": year,
            "month": month,
            "start_date": start_date.date(),
            "end_date": end_date.date(),
        }

        if extraction_mode == "incremental" and last_extraction:
            params["incremental_date"] = (last_extraction - timedelta(days=7))

        # Execute query
        df = self.database.read_sql(query, params)

        # Save to CSV
        output_path = self.data_dir / f"{workflow_id}_{config['output_file']}"
        df.to_csv(output_path, index=False)

        await self._log(
            workflow_id,
            "info",
            f"Extracted {len(df)} records for {dataset_name}"
        )

        return output_path, len(df)

    def _decide_extraction_mode(self, last_extraction_time: Optional[datetime]) -> str:
        """
        Decide whether to do full or incremental extraction.

        Args:
            last_extraction_time: Time of last successful extraction

        Returns:
            "full" or "incremental"
        """
        if last_extraction_time is None:
            return "full"

        hours_since_last = (datetime.now() - last_extraction_time).total_seconds() / 3600

        if hours_since_last < 48:
            return "incremental"
        else:
            return "full"
