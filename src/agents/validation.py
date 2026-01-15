"""Validation Agent for comprehensive data quality checks."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.agents.base import BaseAgent
from src.models.workflow import AgentResult, AgentStatus, WorkflowState
from src.services.state_manager import StateManager
from src.validation.rules import (
    ValidationRule,
    ValidationResult,
    ValidationSeverity,
    RequiredFieldsRule,
    NullValueRule,
    AgeRangeRule,
    CostAmountRule,
    DateLogicRule,
    DuplicateRule,
    GenderDiagnosisRule,
    VolumeConsistencyRule,
)
from src.validation.remediation import AutoRemediation
from src.config import settings

logger = logging.getLogger(__name__)


class ValidationAgent(BaseAgent):
    """Agent for validating extracted data quality."""

    # Required fields by dataset
    REQUIRED_FIELDS = {
        "members": ["member_id", "first_name", "last_name", "date_of_birth", "gender", "hcc_risk_score"],
        "medical_claims": ["claim_id", "member_id", "service_date", "paid_amount"],
        "pharmacy_claims": ["claim_id", "member_id", "fill_date", "paid_amount", "drug_name"],
        "quality_measures": ["measure_id", "measure_name", "measure_category", "numerator", "denominator"],
    }

    # Expected volumes (for consistency checks)
    EXPECTED_VOLUMES = {
        "members": 12000,
        "medical_claims": 50000,
        "pharmacy_claims": 15000,
        "quality_measures": 23,
    }

    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        data_dir: Optional[str] = None
    ):
        super().__init__(name="ValidationAgent", state_manager=state_manager)
        self.data_dir = Path(data_dir or settings.data_dir) / "extracts"

    async def execute(self, workflow_state: WorkflowState) -> AgentResult:
        """Execute data validation."""
        started_at = datetime.now()

        try:
            all_results: List[ValidationResult] = []
            critical_errors: List[Dict] = []
            warnings: List[Dict] = []
            auto_fixes_applied = 0

            # Load and validate each dataset
            for dataset_name in self.REQUIRED_FIELDS.keys():
                file_path = self.data_dir / f"{workflow_state.workflow_id}_{dataset_name}.csv"

                if not file_path.exists():
                    critical_errors.append({
                        "dataset": dataset_name,
                        "error": f"File not found: {file_path}"
                    })
                    continue

                await self._log(
                    workflow_state.workflow_id,
                    "info",
                    f"Validating {dataset_name}..."
                )

                # Load data
                df = pd.read_csv(file_path)

                # Run validation rules
                dataset_results = await self._validate_dataset(
                    workflow_state.workflow_id,
                    dataset_name,
                    df
                )
                all_results.extend(dataset_results)

                # Check for critical errors
                dataset_critical = [
                    r for r in dataset_results
                    if not r.passed and r.severity == ValidationSeverity.CRITICAL
                ]

                # Apply auto-remediation for fixable issues
                if any(r.auto_fixable for r in dataset_results):
                    df, fix_count = await self._apply_remediation(
                        workflow_state.workflow_id,
                        dataset_name,
                        df
                    )
                    auto_fixes_applied += fix_count

                    # Save cleaned data
                    df.to_csv(file_path, index=False)

                # Collect errors and warnings
                for result in dataset_results:
                    if not result.passed:
                        issue = {
                            "dataset": dataset_name,
                            "rule": result.rule_name,
                            "message": result.message,
                            "affected_records": result.affected_records,
                            "affected_pct": result.affected_percentage,
                        }

                        if result.severity == ValidationSeverity.CRITICAL and not result.fix_applied:
                            critical_errors.append(issue)
                        else:
                            warnings.append(issue)

            # Determine overall validation status
            validation_passed = len(critical_errors) == 0

            # Generate validation report
            report_path = await self._generate_report(
                workflow_state.workflow_id,
                all_results,
                auto_fixes_applied
            )

            if not validation_passed:
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.FAILED,
                    started_at=started_at,
                    completed_at=datetime.now(),
                    result_data={
                        "validation_passed": False,
                        "critical_errors": critical_errors,
                        "warnings": warnings,
                        "auto_fixes_applied": auto_fixes_applied,
                        "report_path": str(report_path),
                    },
                    errors=[{
                        "message": f"Validation failed with {len(critical_errors)} critical errors",
                        "critical_errors": critical_errors
                    }]
                )

            return self._create_success_result(
                started_at=started_at,
                result_data={
                    "validation_passed": True,
                    "critical_errors": [],
                    "warnings": warnings,
                    "auto_fixes_applied": auto_fixes_applied,
                    "report_path": str(report_path),
                    "total_checks": len(all_results),
                    "passed_checks": sum(1 for r in all_results if r.passed),
                },
                warnings=[w for w in warnings]
            )

        except Exception as e:
            logger.exception(f"Validation failed: {e}")
            return self._create_failure_result(
                started_at=started_at,
                error_message=str(e)
            )

    async def _validate_dataset(
        self,
        workflow_id: str,
        dataset_name: str,
        df: pd.DataFrame
    ) -> List[ValidationResult]:
        """Run all validation rules on a dataset."""
        results = []

        # 1. Required fields check
        required_fields = self.REQUIRED_FIELDS.get(dataset_name, [])
        rule = RequiredFieldsRule(required_fields)
        results.append(rule.validate(df))

        # 2. Null value checks
        rule = NullValueRule(required_fields)
        results.append(rule.validate(df))

        # 3. Volume consistency check
        expected = self.EXPECTED_VOLUMES.get(dataset_name, len(df))
        rule = VolumeConsistencyRule(expected)
        results.append(rule.validate(df))

        # 4. Duplicate check
        if dataset_name in ["medical_claims", "pharmacy_claims"]:
            rule = DuplicateRule(["claim_id"])
        elif dataset_name == "members":
            rule = DuplicateRule(["member_id"])
        else:
            rule = DuplicateRule(["measure_id"])
        results.append(rule.validate(df))

        # Dataset-specific rules
        if dataset_name == "members":
            # Age range check
            rule = AgeRangeRule("date_of_birth")
            results.append(rule.validate(df))

        elif dataset_name == "medical_claims":
            # Cost amount checks
            rule = CostAmountRule(["paid_amount", "allowed_amount"])
            results.append(rule.validate(df))

            # Date logic checks
            rule = DateLogicRule("service_date", "paid_date")
            results.append(rule.validate(df))

            # Gender-diagnosis consistency
            # Need to join with members for this
            rule = GenderDiagnosisRule()
            results.append(rule.validate(df))

        elif dataset_name == "pharmacy_claims":
            # Cost amount checks
            rule = CostAmountRule(["paid_amount"])
            results.append(rule.validate(df))

        # Log results
        passed = sum(1 for r in results if r.passed)
        await self._log(
            workflow_id,
            "info",
            f"{dataset_name}: {passed}/{len(results)} checks passed"
        )

        return results

    async def _apply_remediation(
        self,
        workflow_id: str,
        dataset_name: str,
        df: pd.DataFrame
    ) -> tuple:
        """Apply auto-remediation to a dataset."""
        await self._log(
            workflow_id,
            "info",
            f"Applying auto-remediation to {dataset_name}..."
        )

        # Configure remediation based on dataset
        config = {
            "date_fields": [],
            "amount_fields": [],
            "key_fields": [],
        }

        if dataset_name == "medical_claims":
            config["date_fields"] = ["service_date", "paid_date"]
            config["amount_fields"] = ["paid_amount", "allowed_amount"]
            config["key_fields"] = ["claim_id"]
        elif dataset_name == "pharmacy_claims":
            config["date_fields"] = ["fill_date"]
            config["amount_fields"] = ["paid_amount"]
            config["key_fields"] = ["claim_id"]
        elif dataset_name == "members":
            config["date_fields"] = ["date_of_birth", "attribution_start_date", "attribution_end_date"]
            config["key_fields"] = ["member_id"]

        df, remediation_results = AutoRemediation.apply_all_remediations(df, config)

        total_fixed = sum(r.records_fixed for r in remediation_results if r.success)

        for result in remediation_results:
            level = "info" if result.success else "warning"
            await self._log(workflow_id, level, result.message)

        return df, total_fixed

    async def _generate_report(
        self,
        workflow_id: str,
        results: List[ValidationResult],
        auto_fixes: int
    ) -> Path:
        """Generate validation report JSON file."""
        report = {
            "workflow_id": workflow_id,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_checks": len(results),
                "passed": sum(1 for r in results if r.passed),
                "failed": sum(1 for r in results if not r.passed),
                "critical_errors": sum(1 for r in results if not r.passed and r.severity == ValidationSeverity.CRITICAL),
                "warnings": sum(1 for r in results if not r.passed and r.severity == ValidationSeverity.WARNING),
                "auto_fixes_applied": auto_fixes,
            },
            "results": [r.to_dict() for r in results]
        }

        report_path = self.data_dir / f"{workflow_id}_validation_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        return report_path
