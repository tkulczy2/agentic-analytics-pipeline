"""FastAPI routes for workflow management."""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks

from src.api.schemas import (
    WorkflowCreate,
    WorkflowResponse,
    LogsResponse,
    LogEntry,
    TestDataConfig,
    TestDataResponse,
    HealthResponse,
)
from src.agents.orchestrator import OrchestratorAgent
from src.services.state_manager import StateManager
from src.services.database import DatabaseService
from src.services.email_service import EmailService
from src.models.workflow import WorkflowStatus

logger = logging.getLogger(__name__)

router = APIRouter()

# Service instances (will be initialized in main.py)
_orchestrator: Optional[OrchestratorAgent] = None
_state_manager: Optional[StateManager] = None
_database: Optional[DatabaseService] = None
_email_service: Optional[EmailService] = None


def get_orchestrator() -> OrchestratorAgent:
    """Get orchestrator instance."""
    global _orchestrator, _state_manager, _database, _email_service
    if _orchestrator is None:
        _state_manager = StateManager()
        _database = DatabaseService()
        _email_service = EmailService()
        _orchestrator = OrchestratorAgent(
            state_manager=_state_manager,
            database=_database,
            email_service=_email_service
        )
    return _orchestrator


def get_state_manager() -> StateManager:
    """Get state manager instance."""
    get_orchestrator()  # Ensure initialized
    return _state_manager


def get_database() -> DatabaseService:
    """Get database instance."""
    get_orchestrator()  # Ensure initialized
    return _database


@router.post("/workflows/", response_model=WorkflowResponse, tags=["workflows"])
async def create_workflow(request: WorkflowCreate):
    """
    Start a new analytics workflow.

    This endpoint starts a new workflow that will:
    1. Extract healthcare data from the database
    2. Validate and clean the data
    3. Calculate financial, quality, and risk metrics
    4. Generate reports and send email notifications
    """
    orchestrator = get_orchestrator()

    try:
        state = await orchestrator.start_workflow(
            contract_id=request.contract_id,
            performance_year=request.performance_year,
            performance_month=request.performance_month
        )

        return WorkflowResponse(
            workflow_id=state.workflow_id,
            contract_id=state.contract_id,
            performance_year=state.performance_year,
            performance_month=state.performance_month,
            status=state.status.value,
            started_at=state.started_at,
            completed_at=state.completed_at,
            data_agent_status=state.data_agent_status.value,
            validation_agent_status=state.validation_agent_status.value,
            analysis_agent_status=state.analysis_agent_status.value,
            reporting_agent_status=state.reporting_agent_status.value,
            extracted_files=state.extracted_files,
            records_extracted=state.records_extracted,
            validation_passed=state.validation_passed,
            critical_errors=state.critical_errors,
            warnings=state.warnings,
            auto_fixes_applied=state.auto_fixes_applied,
            financial_metrics=state.financial_metrics,
            quality_metrics=state.quality_metrics,
            risk_metrics=state.risk_metrics,
            predictions=state.predictions,
            reports_generated=state.reports_generated,
            retry_count=state.retry_count,
            errors=state.errors,
        )

    except Exception as e:
        logger.exception(f"Failed to create workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse, tags=["workflows"])
async def get_workflow(workflow_id: str):
    """Get workflow status and results."""
    state_manager = get_state_manager()

    state = await state_manager.get_workflow(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return WorkflowResponse(
        workflow_id=state.workflow_id,
        contract_id=state.contract_id,
        performance_year=state.performance_year,
        performance_month=state.performance_month,
        status=state.status.value,
        started_at=state.started_at,
        completed_at=state.completed_at,
        data_agent_status=state.data_agent_status.value,
        validation_agent_status=state.validation_agent_status.value,
        analysis_agent_status=state.analysis_agent_status.value,
        reporting_agent_status=state.reporting_agent_status.value,
        extracted_files=state.extracted_files,
        records_extracted=state.records_extracted,
        validation_passed=state.validation_passed,
        critical_errors=state.critical_errors,
        warnings=state.warnings,
        auto_fixes_applied=state.auto_fixes_applied,
        financial_metrics=state.financial_metrics,
        quality_metrics=state.quality_metrics,
        risk_metrics=state.risk_metrics,
        predictions=state.predictions,
        reports_generated=state.reports_generated,
        retry_count=state.retry_count,
        errors=state.errors,
    )


@router.get("/workflows/{workflow_id}/logs", response_model=LogsResponse, tags=["workflows"])
async def get_workflow_logs(workflow_id: str, start: int = 0, count: int = 100):
    """Get workflow execution logs."""
    state_manager = get_state_manager()

    state = await state_manager.get_workflow(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")

    logs = await state_manager.get_logs(workflow_id, start, count)

    return LogsResponse(
        workflow_id=workflow_id,
        logs=[
            LogEntry(
                timestamp=datetime.fromisoformat(log["timestamp"]),
                level=log["level"],
                message=log["message"],
                data=log.get("data", {})
            )
            for log in logs
        ]
    )


@router.post("/workflows/{workflow_id}/pause", response_model=WorkflowResponse, tags=["workflows"])
async def pause_workflow(workflow_id: str):
    """Pause a running workflow."""
    orchestrator = get_orchestrator()

    state = await orchestrator.pause_workflow(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return WorkflowResponse(
        workflow_id=state.workflow_id,
        contract_id=state.contract_id,
        performance_year=state.performance_year,
        performance_month=state.performance_month,
        status=state.status.value,
        started_at=state.started_at,
        completed_at=state.completed_at,
        data_agent_status=state.data_agent_status.value,
        validation_agent_status=state.validation_agent_status.value,
        analysis_agent_status=state.analysis_agent_status.value,
        reporting_agent_status=state.reporting_agent_status.value,
    )


@router.post("/workflows/{workflow_id}/resume", response_model=WorkflowResponse, tags=["workflows"])
async def resume_workflow(workflow_id: str):
    """Resume a paused workflow."""
    orchestrator = get_orchestrator()

    state = await orchestrator.resume_workflow(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return WorkflowResponse(
        workflow_id=state.workflow_id,
        contract_id=state.contract_id,
        performance_year=state.performance_year,
        performance_month=state.performance_month,
        status=state.status.value,
        started_at=state.started_at,
        completed_at=state.completed_at,
        data_agent_status=state.data_agent_status.value,
        validation_agent_status=state.validation_agent_status.value,
        analysis_agent_status=state.analysis_agent_status.value,
        reporting_agent_status=state.reporting_agent_status.value,
    )


@router.post("/workflows/{workflow_id}/cancel", response_model=WorkflowResponse, tags=["workflows"])
async def cancel_workflow(workflow_id: str):
    """Cancel a workflow."""
    orchestrator = get_orchestrator()

    state = await orchestrator.cancel_workflow(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return WorkflowResponse(
        workflow_id=state.workflow_id,
        contract_id=state.contract_id,
        performance_year=state.performance_year,
        performance_month=state.performance_month,
        status=state.status.value,
        started_at=state.started_at,
        completed_at=state.completed_at,
        data_agent_status=state.data_agent_status.value,
        validation_agent_status=state.validation_agent_status.value,
        analysis_agent_status=state.analysis_agent_status.value,
        reporting_agent_status=state.reporting_agent_status.value,
    )


@router.get("/contracts/{contract_id}/workflows", response_model=List[WorkflowResponse], tags=["contracts"])
async def list_contract_workflows(contract_id: str, status: Optional[str] = None):
    """List all workflows for a contract."""
    state_manager = get_state_manager()

    status_filter = WorkflowStatus(status) if status else None
    workflows = await state_manager.list_workflows(contract_id=contract_id, status=status_filter)

    return [
        WorkflowResponse(
            workflow_id=state.workflow_id,
            contract_id=state.contract_id,
            performance_year=state.performance_year,
            performance_month=state.performance_month,
            status=state.status.value,
            started_at=state.started_at,
            completed_at=state.completed_at,
            data_agent_status=state.data_agent_status.value,
            validation_agent_status=state.validation_agent_status.value,
            analysis_agent_status=state.analysis_agent_status.value,
            reporting_agent_status=state.reporting_agent_status.value,
        )
        for state in workflows
    ]


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """System health check for database, Redis, and SMTP connectivity."""
    state_manager = get_state_manager()
    database = get_database()

    db_healthy = await database.health_check()
    redis_healthy = await state_manager.health_check()

    email_service = EmailService()
    smtp_healthy = await email_service.health_check()

    overall_status = "healthy" if all([db_healthy, redis_healthy, smtp_healthy]) else "unhealthy"

    return HealthResponse(
        status=overall_status,
        database=db_healthy,
        redis=redis_healthy,
        smtp=smtp_healthy,
        timestamp=datetime.now()
    )


@router.post("/test-data/generate", response_model=TestDataResponse, tags=["test-data"])
async def generate_test_data(config: TestDataConfig):
    """Generate test data with specified configuration."""
    from scripts.generate_test_data import TestDataGenerator

    try:
        database = get_database()
        generator = TestDataGenerator(database)

        records_created = await generator.generate_all(config)

        return TestDataResponse(
            success=True,
            message="Test data generated successfully",
            records_created=records_created
        )

    except Exception as e:
        logger.exception(f"Failed to generate test data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
