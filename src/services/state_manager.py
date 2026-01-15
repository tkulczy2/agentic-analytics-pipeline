"""Redis-based state management for workflow persistence."""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

from src.config import settings
from src.models.workflow import WorkflowState, WorkflowStatus

logger = logging.getLogger(__name__)


class StateManager:
    """Manages workflow state persistence in Redis."""

    WORKFLOW_PREFIX = "workflow:"
    WORKFLOW_LIST_KEY = "workflows:all"
    CONTRACT_WORKFLOWS_PREFIX = "contract_workflows:"
    LOG_PREFIX = "workflow_logs:"

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize the state manager."""
        self.redis_url = redis_url or settings.redis_url
        self._client: Optional[redis.Redis] = None

    async def connect(self):
        """Establish connection to Redis."""
        if self._client is None:
            self._client = redis.from_url(self.redis_url, decode_responses=True)
            logger.info("Connected to Redis")

    async def disconnect(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Disconnected from Redis")

    async def health_check(self) -> bool:
        """Check if Redis is accessible."""
        try:
            await self.connect()
            await self._client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    async def save_workflow(self, state: WorkflowState) -> None:
        """Save workflow state to Redis."""
        await self.connect()
        key = f"{self.WORKFLOW_PREFIX}{state.workflow_id}"

        # Save workflow state
        await self._client.set(key, state.to_json())

        # Add to workflow list
        await self._client.sadd(self.WORKFLOW_LIST_KEY, state.workflow_id)

        # Add to contract-specific list
        contract_key = f"{self.CONTRACT_WORKFLOWS_PREFIX}{state.contract_id}"
        await self._client.sadd(contract_key, state.workflow_id)

        logger.debug(f"Saved workflow state: {state.workflow_id}")

    async def get_workflow(self, workflow_id: str) -> Optional[WorkflowState]:
        """Retrieve workflow state from Redis."""
        await self.connect()
        key = f"{self.WORKFLOW_PREFIX}{workflow_id}"
        data = await self._client.get(key)

        if data:
            return WorkflowState.from_json(data)
        return None

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete workflow state from Redis."""
        await self.connect()

        state = await self.get_workflow(workflow_id)
        if not state:
            return False

        key = f"{self.WORKFLOW_PREFIX}{workflow_id}"
        await self._client.delete(key)

        # Remove from workflow list
        await self._client.srem(self.WORKFLOW_LIST_KEY, workflow_id)

        # Remove from contract-specific list
        contract_key = f"{self.CONTRACT_WORKFLOWS_PREFIX}{state.contract_id}"
        await self._client.srem(contract_key, workflow_id)

        # Delete logs
        log_key = f"{self.LOG_PREFIX}{workflow_id}"
        await self._client.delete(log_key)

        logger.debug(f"Deleted workflow: {workflow_id}")
        return True

    async def list_workflows(
        self,
        contract_id: Optional[str] = None,
        status: Optional[WorkflowStatus] = None
    ) -> List[WorkflowState]:
        """List all workflows, optionally filtered by contract or status."""
        await self.connect()

        if contract_id:
            contract_key = f"{self.CONTRACT_WORKFLOWS_PREFIX}{contract_id}"
            workflow_ids = await self._client.smembers(contract_key)
        else:
            workflow_ids = await self._client.smembers(self.WORKFLOW_LIST_KEY)

        workflows = []
        for wf_id in workflow_ids:
            state = await self.get_workflow(wf_id)
            if state:
                if status is None or state.status == status:
                    workflows.append(state)

        # Sort by started_at descending
        workflows.sort(key=lambda w: w.started_at, reverse=True)
        return workflows

    async def update_workflow_status(
        self,
        workflow_id: str,
        status: WorkflowStatus,
        error: Optional[Dict[str, Any]] = None
    ) -> Optional[WorkflowState]:
        """Update workflow status."""
        state = await self.get_workflow(workflow_id)
        if not state:
            return None

        state.status = status
        if status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED):
            state.completed_at = datetime.now()

        if error:
            state.errors.append(error)

        await self.save_workflow(state)
        return state

    async def add_log(self, workflow_id: str, level: str, message: str, data: Optional[Dict] = None):
        """Add a log entry for a workflow."""
        await self.connect()
        log_key = f"{self.LOG_PREFIX}{workflow_id}"

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "data": data or {}
        }

        await self._client.rpush(log_key, json.dumps(log_entry))

        # Keep only last 1000 log entries
        await self._client.ltrim(log_key, -1000, -1)

    async def get_logs(
        self,
        workflow_id: str,
        start: int = 0,
        count: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve log entries for a workflow."""
        await self.connect()
        log_key = f"{self.LOG_PREFIX}{workflow_id}"

        log_entries = await self._client.lrange(log_key, start, start + count - 1)
        return [json.loads(entry) for entry in log_entries]

    async def get_last_extraction_time(self, contract_id: str) -> Optional[datetime]:
        """Get the last successful extraction time for a contract."""
        workflows = await self.list_workflows(
            contract_id=contract_id,
            status=WorkflowStatus.COMPLETED
        )

        if workflows:
            # workflows are already sorted by started_at descending
            return workflows[0].completed_at

        return None
