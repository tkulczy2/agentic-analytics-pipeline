"""Orchestrator Agent for coordinating the analytics pipeline."""
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.agents.data_extraction import DataExtractionAgent
from src.agents.validation import ValidationAgent
from src.agents.analysis import AnalysisAgent
from src.agents.reporting import ReportingAgent
from src.models.workflow import (
    AgentResult,
    AgentStatus,
    WorkflowState,
    WorkflowStatus,
)
from src.services.state_manager import StateManager
from src.services.database import DatabaseService
from src.services.email_service import EmailService
from src.config import settings

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Master controller that coordinates all pipeline agents."""

    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        database: Optional[DatabaseService] = None,
        email_service: Optional[EmailService] = None
    ):
        super().__init__(name="OrchestratorAgent", state_manager=state_manager)
        self.database = database or DatabaseService()
        self.email_service = email_service or EmailService()

        # Initialize child agents
        self.data_agent = DataExtractionAgent(
            state_manager=self.state_manager,
            database=self.database
        )
        self.validation_agent = ValidationAgent(state_manager=self.state_manager)
        self.analysis_agent = AnalysisAgent(state_manager=self.state_manager)
        self.reporting_agent = ReportingAgent(state_manager=self.state_manager)

    async def start_workflow(
        self,
        contract_id: str,
        performance_year: int,
        performance_month: int
    ) -> WorkflowState:
        """
        Start a new analytics workflow.

        Args:
            contract_id: Contract identifier
            performance_year: Performance year (e.g., 2024)
            performance_month: Performance month (1-12)

        Returns:
            WorkflowState for the started workflow
        """
        workflow_id = f"wf-{uuid.uuid4().hex[:12]}"

        state = WorkflowState(
            workflow_id=workflow_id,
            contract_id=contract_id,
            performance_year=performance_year,
            performance_month=performance_month,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now(),
        )

        await self.state_manager.save_workflow(state)
        await self._log(workflow_id, "info", f"Started workflow for {contract_id} {performance_year}-M{performance_month:02d}")

        # Execute workflow asynchronously
        asyncio.create_task(self._execute_workflow(state))

        return state

    async def _execute_workflow(self, state: WorkflowState):
        """Execute the complete workflow pipeline."""
        try:
            # Stage 1: Data Extraction
            state.data_agent_status = AgentStatus.RUNNING
            await self.state_manager.save_workflow(state)

            data_result = await self.data_agent.run(state)
            state.data_agent_status = data_result.status
            state.agent_results.append(data_result.to_dict())

            if data_result.status == AgentStatus.FAILED:
                await self._handle_critical_failure(state, data_result, "Data Extraction")
                return

            # Update state with extraction results
            state.extracted_files = data_result.result_data.get("extracted_files", [])
            state.records_extracted = data_result.result_data.get("records_extracted", {})
            await self.state_manager.save_workflow(state)

            # Stage 2: Validation
            state.validation_agent_status = AgentStatus.RUNNING
            await self.state_manager.save_workflow(state)

            validation_result = await self.validation_agent.run(state)
            state.validation_agent_status = validation_result.status
            state.agent_results.append(validation_result.to_dict())

            if validation_result.status == AgentStatus.FAILED:
                # Check if it's a critical failure
                critical_errors = validation_result.result_data.get("critical_errors", [])
                if critical_errors:
                    state.critical_errors = critical_errors
                    await self._handle_critical_failure(state, validation_result, "Validation")
                    return

            # Update state with validation results
            state.validation_passed = validation_result.result_data.get("validation_passed", False)
            state.warnings = validation_result.result_data.get("warnings", [])
            state.auto_fixes_applied = validation_result.result_data.get("auto_fixes_applied", 0)
            await self.state_manager.save_workflow(state)

            # Stage 3: Analysis
            state.analysis_agent_status = AgentStatus.RUNNING
            await self.state_manager.save_workflow(state)

            analysis_result = await self.analysis_agent.run(state)
            state.analysis_agent_status = analysis_result.status
            state.agent_results.append(analysis_result.to_dict())

            if analysis_result.status == AgentStatus.FAILED:
                # Analysis failure is not critical, we can continue with warnings
                state.warnings.append({
                    "agent": "Analysis",
                    "message": "Analysis completed with errors",
                    "errors": analysis_result.errors
                })
            else:
                # Update state with analysis results
                state.financial_metrics = analysis_result.result_data.get("financial_metrics")
                state.quality_metrics = analysis_result.result_data.get("quality_metrics")
                state.risk_metrics = analysis_result.result_data.get("risk_metrics")
                state.predictions = analysis_result.result_data.get("predictions")

            await self.state_manager.save_workflow(state)

            # Stage 4: Reporting
            state.reporting_agent_status = AgentStatus.RUNNING
            await self.state_manager.save_workflow(state)

            reporting_result = await self.reporting_agent.run(state)
            state.reporting_agent_status = reporting_result.status
            state.agent_results.append(reporting_result.to_dict())

            if reporting_result.status == AgentStatus.COMPLETED:
                state.reports_generated = reporting_result.result_data.get("reports_generated", [])

            # Mark workflow as completed
            state.status = WorkflowStatus.COMPLETED
            state.completed_at = datetime.now()
            await self.state_manager.save_workflow(state)

            await self._log(
                state.workflow_id,
                "info",
                f"Workflow completed successfully in {(state.completed_at - state.started_at).total_seconds():.1f}s"
            )

        except Exception as e:
            logger.exception(f"Workflow execution failed: {e}")
            state.status = WorkflowStatus.FAILED
            state.completed_at = datetime.now()
            state.errors.append({
                "agent": "Orchestrator",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            await self.state_manager.save_workflow(state)

            # Send failure notification
            await self.email_service.send_workflow_failure(
                workflow_id=state.workflow_id,
                contract_id=state.contract_id,
                error_message=str(e),
                errors=state.errors
            )

    async def _handle_critical_failure(
        self,
        state: WorkflowState,
        result: AgentResult,
        stage_name: str
    ):
        """Handle a critical agent failure."""
        state.status = WorkflowStatus.FAILED
        state.completed_at = datetime.now()
        state.errors.extend(result.errors)

        await self.state_manager.save_workflow(state)

        await self._log(
            state.workflow_id,
            "error",
            f"Workflow failed at {stage_name} stage"
        )

        # Send failure notification
        await self.email_service.send_workflow_failure(
            workflow_id=state.workflow_id,
            contract_id=state.contract_id,
            error_message=f"Critical failure in {stage_name}",
            errors=state.errors
        )

    async def pause_workflow(self, workflow_id: str) -> Optional[WorkflowState]:
        """Pause a running workflow."""
        state = await self.state_manager.get_workflow(workflow_id)
        if not state:
            return None

        if state.status == WorkflowStatus.RUNNING:
            state.status = WorkflowStatus.PAUSED
            await self.state_manager.save_workflow(state)
            await self._log(workflow_id, "info", "Workflow paused")

        return state

    async def resume_workflow(self, workflow_id: str) -> Optional[WorkflowState]:
        """Resume a paused workflow."""
        state = await self.state_manager.get_workflow(workflow_id)
        if not state:
            return None

        if state.status == WorkflowStatus.PAUSED:
            state.status = WorkflowStatus.RUNNING
            await self.state_manager.save_workflow(state)
            await self._log(workflow_id, "info", "Workflow resumed")

            # Resume execution
            asyncio.create_task(self._resume_execution(state))

        return state

    async def _resume_execution(self, state: WorkflowState):
        """Resume workflow execution from where it was paused."""
        try:
            # Determine which stage to resume from
            if state.validation_agent_status == AgentStatus.PENDING:
                # Resume from validation
                state.validation_agent_status = AgentStatus.RUNNING
                await self.state_manager.save_workflow(state)

                validation_result = await self.validation_agent.run(state)
                state.validation_agent_status = validation_result.status
                state.agent_results.append(validation_result.to_dict())

                if validation_result.status == AgentStatus.FAILED:
                    critical_errors = validation_result.result_data.get("critical_errors", [])
                    if critical_errors:
                        await self._handle_critical_failure(state, validation_result, "Validation")
                        return

                state.validation_passed = validation_result.result_data.get("validation_passed", False)
                state.warnings = validation_result.result_data.get("warnings", [])
                state.auto_fixes_applied = validation_result.result_data.get("auto_fixes_applied", 0)

            if state.analysis_agent_status == AgentStatus.PENDING:
                # Continue to analysis
                state.analysis_agent_status = AgentStatus.RUNNING
                await self.state_manager.save_workflow(state)

                analysis_result = await self.analysis_agent.run(state)
                state.analysis_agent_status = analysis_result.status
                state.agent_results.append(analysis_result.to_dict())

                if analysis_result.status == AgentStatus.COMPLETED:
                    state.financial_metrics = analysis_result.result_data.get("financial_metrics")
                    state.quality_metrics = analysis_result.result_data.get("quality_metrics")
                    state.risk_metrics = analysis_result.result_data.get("risk_metrics")
                    state.predictions = analysis_result.result_data.get("predictions")

            if state.reporting_agent_status == AgentStatus.PENDING:
                # Continue to reporting
                state.reporting_agent_status = AgentStatus.RUNNING
                await self.state_manager.save_workflow(state)

                reporting_result = await self.reporting_agent.run(state)
                state.reporting_agent_status = reporting_result.status
                state.agent_results.append(reporting_result.to_dict())

                if reporting_result.status == AgentStatus.COMPLETED:
                    state.reports_generated = reporting_result.result_data.get("reports_generated", [])

            # Complete workflow
            state.status = WorkflowStatus.COMPLETED
            state.completed_at = datetime.now()
            await self.state_manager.save_workflow(state)

            await self._log(state.workflow_id, "info", "Resumed workflow completed")

        except Exception as e:
            logger.exception(f"Resumed workflow failed: {e}")
            state.status = WorkflowStatus.FAILED
            state.completed_at = datetime.now()
            state.errors.append({
                "agent": "Orchestrator",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            await self.state_manager.save_workflow(state)

    async def cancel_workflow(self, workflow_id: str) -> Optional[WorkflowState]:
        """Cancel a running or paused workflow."""
        state = await self.state_manager.get_workflow(workflow_id)
        if not state:
            return None

        if state.status in (WorkflowStatus.RUNNING, WorkflowStatus.PAUSED):
            state.status = WorkflowStatus.CANCELLED
            state.completed_at = datetime.now()
            await self.state_manager.save_workflow(state)
            await self._log(workflow_id, "info", "Workflow cancelled")

        return state

    async def execute(self, workflow_state: WorkflowState) -> AgentResult:
        """Execute method required by base class (not used directly)."""
        # This agent starts workflows via start_workflow() instead
        return self._create_success_result(
            started_at=datetime.now(),
            result_data={"message": "Use start_workflow() to begin a workflow"}
        )
