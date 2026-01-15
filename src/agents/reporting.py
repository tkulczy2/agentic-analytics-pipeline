"""Reporting Agent for generating PowerPoint reports and email distribution."""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.models.workflow import AgentResult, AgentStatus, WorkflowState
from src.services.state_manager import StateManager
from src.services.report_generator import ReportGenerator
from src.services.email_service import EmailService
from src.config import settings

logger = logging.getLogger(__name__)


class ReportingAgent(BaseAgent):
    """Agent for generating reports and distributing via email."""

    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        report_generator: Optional[ReportGenerator] = None,
        email_service: Optional[EmailService] = None
    ):
        super().__init__(name="ReportingAgent", state_manager=state_manager)
        self.report_generator = report_generator or ReportGenerator()
        self.email_service = email_service or EmailService()

    async def execute(self, workflow_state: WorkflowState) -> AgentResult:
        """Execute report generation and distribution."""
        started_at = datetime.now()

        try:
            # Get metrics from workflow state
            financial_metrics = workflow_state.financial_metrics or {}
            quality_metrics = workflow_state.quality_metrics or {}
            risk_metrics = workflow_state.risk_metrics or {}
            predictions = workflow_state.predictions or {}

            reports_generated = []

            # Generate Executive Report
            await self._log(
                workflow_state.workflow_id,
                "info",
                "Generating executive report..."
            )

            exec_report_path = self.report_generator.generate_executive_report(
                workflow_id=workflow_state.workflow_id,
                contract_id=workflow_state.contract_id,
                performance_year=workflow_state.performance_year,
                performance_month=workflow_state.performance_month,
                financial_metrics=financial_metrics,
                quality_metrics=quality_metrics,
                risk_metrics=risk_metrics,
                predictions=predictions,
            )
            reports_generated.append(str(exec_report_path))

            # Send email notifications
            await self._log(
                workflow_state.workflow_id,
                "info",
                "Sending email notifications..."
            )

            # Executive stakeholders
            exec_email_sent = await self.email_service.send_workflow_completion(
                workflow_id=workflow_state.workflow_id,
                contract_id=workflow_state.contract_id,
                performance_year=workflow_state.performance_year,
                performance_month=workflow_state.performance_month,
                summary={
                    "financial": financial_metrics,
                    "quality": quality_metrics,
                    "risk": risk_metrics,
                    "predictions": predictions,
                },
                report_path=exec_report_path,
                report_type="executive"
            )

            # Analytics team
            analytics_email_sent = await self.email_service.send_workflow_completion(
                workflow_id=workflow_state.workflow_id,
                contract_id=workflow_state.contract_id,
                performance_year=workflow_state.performance_year,
                performance_month=workflow_state.performance_month,
                summary={
                    "financial": financial_metrics,
                    "quality": quality_metrics,
                    "risk": risk_metrics,
                    "predictions": predictions,
                },
                report_path=exec_report_path,
                report_type="analytics"
            )

            # Operations team (if there are high-risk members)
            ops_email_sent = False
            if risk_metrics.get("high_risk_pct", 0) > 20:
                ops_email_sent = await self.email_service.send_workflow_completion(
                    workflow_id=workflow_state.workflow_id,
                    contract_id=workflow_state.contract_id,
                    performance_year=workflow_state.performance_year,
                    performance_month=workflow_state.performance_month,
                    summary={
                        "financial": financial_metrics,
                        "quality": quality_metrics,
                        "risk": risk_metrics,
                        "predictions": predictions,
                    },
                    report_path=exec_report_path,
                    report_type="operations"
                )

            return self._create_success_result(
                started_at=started_at,
                result_data={
                    "reports_generated": reports_generated,
                    "emails_sent": {
                        "executive": exec_email_sent,
                        "analytics": analytics_email_sent,
                        "operations": ops_email_sent,
                    }
                }
            )

        except Exception as e:
            logger.exception(f"Reporting failed: {e}")
            return self._create_failure_result(
                started_at=started_at,
                error_message=str(e)
            )
