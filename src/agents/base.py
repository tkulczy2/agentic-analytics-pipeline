"""Base agent class for the analytics pipeline."""
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from src.models.workflow import AgentResult, AgentStatus, WorkflowState
from src.services.state_manager import StateManager
from src.config import settings

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all pipeline agents."""

    def __init__(
        self,
        name: str,
        state_manager: Optional[StateManager] = None,
        max_retries: int = None,
        retry_delay_base: float = None
    ):
        """
        Initialize the agent.

        Args:
            name: Agent name for logging and tracking
            state_manager: StateManager instance for persistence
            max_retries: Maximum retry attempts (default from settings)
            retry_delay_base: Base delay for exponential backoff
        """
        self.name = name
        self.state_manager = state_manager or StateManager()
        self.max_retries = max_retries or settings.max_retries
        self.retry_delay_base = retry_delay_base or settings.retry_delay_base

    @abstractmethod
    async def execute(self, workflow_state: WorkflowState) -> AgentResult:
        """
        Execute the agent's main logic.

        Args:
            workflow_state: Current workflow state

        Returns:
            AgentResult with execution results
        """
        pass

    async def run(self, workflow_state: WorkflowState) -> AgentResult:
        """
        Run the agent with retry logic.

        Args:
            workflow_state: Current workflow state

        Returns:
            AgentResult with execution results
        """
        result = AgentResult(
            agent_name=self.name,
            status=AgentStatus.RUNNING,
            started_at=datetime.now()
        )

        await self._log(workflow_state.workflow_id, "info", f"Starting {self.name}")

        retry_count = 0
        last_error = None

        while retry_count <= self.max_retries:
            try:
                result = await self.execute(workflow_state)
                result.completed_at = datetime.now()

                if result.status == AgentStatus.COMPLETED:
                    await self._log(
                        workflow_state.workflow_id,
                        "info",
                        f"{self.name} completed successfully"
                    )
                    return result

                # If failed but retryable
                if result.status == AgentStatus.FAILED and retry_count < self.max_retries:
                    raise Exception(f"Agent returned failure: {result.errors}")

                return result

            except Exception as e:
                last_error = str(e)
                retry_count += 1

                if retry_count <= self.max_retries:
                    delay = self.retry_delay_base ** retry_count
                    await self._log(
                        workflow_state.workflow_id,
                        "warning",
                        f"{self.name} failed (attempt {retry_count}/{self.max_retries}), retrying in {delay}s: {last_error}"
                    )
                    await asyncio.sleep(delay)
                else:
                    await self._log(
                        workflow_state.workflow_id,
                        "error",
                        f"{self.name} failed after {self.max_retries} retries: {last_error}"
                    )

        # All retries exhausted
        result.status = AgentStatus.FAILED
        result.completed_at = datetime.now()
        result.errors.append({
            "error": last_error,
            "retries_exhausted": True,
            "retry_count": retry_count
        })

        return result

    async def _log(
        self,
        workflow_id: str,
        level: str,
        message: str,
        data: Optional[Dict] = None
    ):
        """Log a message for the workflow."""
        logger.log(
            getattr(logging, level.upper()),
            f"[{workflow_id}] [{self.name}] {message}"
        )
        await self.state_manager.add_log(workflow_id, level, f"[{self.name}] {message}", data)

    def _create_success_result(
        self,
        started_at: datetime,
        result_data: Dict[str, Any] = None,
        warnings: list = None
    ) -> AgentResult:
        """Create a successful AgentResult."""
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            started_at=started_at,
            completed_at=datetime.now(),
            result_data=result_data or {},
            warnings=warnings or []
        )

    def _create_failure_result(
        self,
        started_at: datetime,
        error_message: str,
        error_details: Dict = None
    ) -> AgentResult:
        """Create a failed AgentResult."""
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.FAILED,
            started_at=started_at,
            completed_at=datetime.now(),
            errors=[{
                "message": error_message,
                "details": error_details or {},
                "timestamp": datetime.now().isoformat()
            }]
        )
