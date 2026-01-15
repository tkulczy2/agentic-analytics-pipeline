"""Analysis Agent for calculating MSSP financial and quality metrics."""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np

from src.agents.base import BaseAgent
from src.models.workflow import AgentResult, AgentStatus, WorkflowState
from src.models.financial import FinancialMetrics
from src.models.quality import QualityMetrics
from src.models.risk import RiskStratification
from src.models.predictions import Predictions
from src.services.state_manager import StateManager
from src.config import settings

logger = logging.getLogger(__name__)


class AnalysisAgent(BaseAgent):
    """Agent for calculating MSSP analytics metrics."""

    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        data_dir: Optional[str] = None
    ):
        super().__init__(name="AnalysisAgent", state_manager=state_manager)
        self.data_dir = Path(data_dir or settings.data_dir) / "extracts"

    async def execute(self, workflow_state: WorkflowState) -> AgentResult:
        """Execute analytics calculations."""
        started_at = datetime.now()

        try:
            # Load validated data
            members_df = self._load_data(workflow_state.workflow_id, "members")
            medical_claims_df = self._load_data(workflow_state.workflow_id, "medical_claims")
            pharmacy_claims_df = self._load_data(workflow_state.workflow_id, "pharmacy_claims")
            quality_df = self._load_data(workflow_state.workflow_id, "quality_measures")

            # Calculate all metrics
            await self._log(workflow_state.workflow_id, "info", "Calculating financial metrics...")
            financial_metrics = self._calculate_financial_metrics(
                members_df,
                medical_claims_df,
                pharmacy_claims_df,
                workflow_state.performance_year,
                workflow_state.performance_month
            )

            await self._log(workflow_state.workflow_id, "info", "Calculating quality metrics...")
            quality_metrics = self._calculate_quality_metrics(
                quality_df,
                workflow_state.performance_year,
                workflow_state.performance_month
            )

            await self._log(workflow_state.workflow_id, "info", "Calculating risk stratification...")
            risk_metrics = self._calculate_risk_stratification(
                members_df,
                medical_claims_df,
                pharmacy_claims_df,
                workflow_state.performance_year,
                workflow_state.performance_month
            )

            await self._log(workflow_state.workflow_id, "info", "Generating predictions...")
            predictions = self._generate_predictions(
                financial_metrics,
                quality_metrics,
                risk_metrics,
                workflow_state.performance_month
            )

            return self._create_success_result(
                started_at=started_at,
                result_data={
                    "financial_metrics": financial_metrics.to_dict(),
                    "quality_metrics": quality_metrics.to_dict(),
                    "risk_metrics": risk_metrics.to_dict(),
                    "predictions": predictions.to_dict(),
                }
            )

        except Exception as e:
            logger.exception(f"Analysis failed: {e}")
            return self._create_failure_result(
                started_at=started_at,
                error_message=str(e)
            )

    def _load_data(self, workflow_id: str, dataset_name: str) -> pd.DataFrame:
        """Load a validated dataset."""
        file_path = self.data_dir / f"{workflow_id}_{dataset_name}.csv"
        return pd.read_csv(file_path)

    def _calculate_financial_metrics(
        self,
        members_df: pd.DataFrame,
        medical_df: pd.DataFrame,
        pharmacy_df: pd.DataFrame,
        year: int,
        month: int
    ) -> FinancialMetrics:
        """Calculate MSSP financial metrics."""
        metrics = FinancialMetrics(
            baseline_spending=settings.baseline_spending,
            shared_savings_rate=settings.shared_savings_rate,
            target_reduction_pct=settings.target_reduction_pct,
            performance_year=year,
            performance_month=month,
        )

        # Calculate member months
        # Assuming monthly data, each member with attribution represents 1 member-month per month
        metrics.average_members = len(members_df)
        metrics.member_months = metrics.average_members * month

        # Calculate spending
        metrics.medical_spending = medical_df["paid_amount"].sum()
        metrics.pharmacy_spending = pharmacy_df["paid_amount"].sum()
        metrics.actual_spending = metrics.medical_spending + metrics.pharmacy_spending

        # Annualize spending for comparison to annual baseline
        if month > 0:
            annualization_factor = 12 / month
            metrics.actual_spending = metrics.actual_spending * annualization_factor

        # Calculate utilization
        if "er_visit" in medical_df.columns:
            metrics.total_er_visits = medical_df["er_visit"].sum() if medical_df["er_visit"].dtype == bool else (medical_df["er_visit"] == True).sum()
        if "inpatient_admit" in medical_df.columns:
            metrics.total_admits = medical_df["inpatient_admit"].sum() if medical_df["inpatient_admit"].dtype == bool else (medical_df["inpatient_admit"] == True).sum()

        # Calculate derived metrics
        metrics.calculate_derived_metrics()

        return metrics

    def _calculate_quality_metrics(
        self,
        quality_df: pd.DataFrame,
        year: int,
        month: int
    ) -> QualityMetrics:
        """Calculate MSSP quality metrics."""
        metrics = QualityMetrics(
            performance_year=year,
            performance_month=month,
        )

        if quality_df.empty:
            return metrics

        # Calculate category scores
        category_scores = {}

        for category in ["preventive_care", "chronic_disease", "care_coordination", "patient_experience"]:
            category_df = quality_df[quality_df["measure_category"] == category]

            if not category_df.empty:
                # Weighted average of performance rates
                if "measure_weight" in category_df.columns:
                    weights = category_df["measure_weight"].fillna(1.0)
                    rates = category_df["performance_rate"].fillna(0)
                    if weights.sum() > 0:
                        category_scores[category] = (rates * weights).sum() / weights.sum()
                    else:
                        category_scores[category] = rates.mean()
                else:
                    category_scores[category] = category_df["performance_rate"].mean()
            else:
                category_scores[category] = 0.0

        metrics.preventive_care_score = category_scores.get("preventive_care", 0.0)
        metrics.chronic_disease_score = category_scores.get("chronic_disease", 0.0)
        metrics.care_coordination_score = category_scores.get("care_coordination", 0.0)
        metrics.patient_experience_score = category_scores.get("patient_experience", 0.0)

        # Store individual measures
        metrics.measures = quality_df.to_dict(orient="records")

        # Calculate composite score
        metrics.calculate_composite_score()

        return metrics

    def _calculate_risk_stratification(
        self,
        members_df: pd.DataFrame,
        medical_df: pd.DataFrame,
        pharmacy_df: pd.DataFrame,
        year: int,
        month: int
    ) -> RiskStratification:
        """Calculate risk stratification metrics."""
        risk = RiskStratification(
            performance_year=year,
            performance_month=month,
        )

        if members_df.empty:
            return risk

        risk.total_members = len(members_df)

        # Categorize members by risk score
        if "hcc_risk_score" in members_df.columns:
            scores = members_df["hcc_risk_score"].fillna(1.0)

            risk.low_risk_count = (scores < RiskStratification.LOW_RISK_MAX).sum()
            risk.high_risk_count = (scores > RiskStratification.HIGH_RISK_MIN).sum()
            risk.medium_risk_count = risk.total_members - risk.low_risk_count - risk.high_risk_count

            risk.average_risk_score = scores.mean()

        # Calculate spending by risk category
        members_with_risk = members_df[["member_id", "hcc_risk_score"]].copy()
        members_with_risk["risk_cat"] = members_with_risk["hcc_risk_score"].apply(
            RiskStratification.categorize_risk
        )

        # Merge with claims
        if not medical_df.empty:
            medical_by_member = medical_df.groupby("member_id")["paid_amount"].sum().reset_index()
            medical_by_member.columns = ["member_id", "medical_spend"]
        else:
            medical_by_member = pd.DataFrame(columns=["member_id", "medical_spend"])

        if not pharmacy_df.empty:
            pharmacy_by_member = pharmacy_df.groupby("member_id")["paid_amount"].sum().reset_index()
            pharmacy_by_member.columns = ["member_id", "pharmacy_spend"]
        else:
            pharmacy_by_member = pd.DataFrame(columns=["member_id", "pharmacy_spend"])

        member_spend = members_with_risk.merge(medical_by_member, on="member_id", how="left")
        member_spend = member_spend.merge(pharmacy_by_member, on="member_id", how="left")
        member_spend["total_spend"] = member_spend["medical_spend"].fillna(0) + member_spend["pharmacy_spend"].fillna(0)

        # Calculate PMPM by risk category
        for cat in ["Low", "Medium", "High"]:
            cat_data = member_spend[member_spend["risk_cat"] == cat]
            if len(cat_data) > 0:
                total_spend = cat_data["total_spend"].sum()
                member_months = len(cat_data) * month

                if cat == "Low":
                    risk.low_risk_spending = total_spend
                    risk.low_risk_pmpm = total_spend / member_months if member_months > 0 else 0
                elif cat == "Medium":
                    risk.medium_risk_spending = total_spend
                    risk.medium_risk_pmpm = total_spend / member_months if member_months > 0 else 0
                else:
                    risk.high_risk_spending = total_spend
                    risk.high_risk_pmpm = total_spend / member_months if member_months > 0 else 0

        return risk

    def _generate_predictions(
        self,
        financial: FinancialMetrics,
        quality: QualityMetrics,
        risk: RiskStratification,
        current_month: int
    ) -> Predictions:
        """Generate year-end predictions."""
        predictions = Predictions(
            current_month=current_month,
            performance_year=financial.performance_year,
        )

        # Project year-end spending
        if current_month > 0 and financial.actual_spending > 0:
            # De-annualize current spending to get YTD
            ytd_spending = financial.actual_spending * (current_month / 12)

            projections = Predictions.project_year_end(
                current_month=current_month,
                ytd_spending=ytd_spending,
                baseline_spending=financial.baseline_spending,
            )

            predictions.projected_year_end_spending = projections.get("projected_spending", 0)
            predictions.projected_year_end_savings = projections.get("projected_savings", 0)
            predictions.savings_lower_bound = projections.get("savings_lower_bound", 0)
            predictions.savings_upper_bound = projections.get("savings_upper_bound", 0)

            if financial.baseline_spending > 0:
                predictions.projected_savings_percentage = (
                    predictions.projected_year_end_savings / financial.baseline_spending * 100
                )

            if predictions.projected_year_end_savings > 0:
                predictions.projected_shared_savings = (
                    predictions.projected_year_end_savings * financial.shared_savings_rate
                )

            # Calculate probability of achieving target
            std_dev = financial.baseline_spending * 0.10  # 10% standard deviation assumption
            target_savings = financial.baseline_spending * financial.target_reduction_pct

            predictions.probability_meeting_target = Predictions.calculate_probability(
                predictions.projected_year_end_savings,
                target_savings,
                std_dev
            )

            predictions.probability_shared_savings = Predictions.calculate_probability(
                predictions.projected_year_end_savings,
                0,  # Just need positive savings
                std_dev
            )

        # Project quality score
        predictions.projected_quality_score = quality.composite_score

        quality_std_dev = 5.0  # Assume 5% standard deviation
        predictions.probability_quality_gate = Predictions.calculate_probability(
            quality.composite_score,
            quality.quality_threshold,
            quality_std_dev
        )

        # Identify risks and opportunities
        predictions.identify_risks_and_opportunities(
            financial.to_dict(),
            quality.to_dict(),
            risk.to_dict()
        )

        return predictions
