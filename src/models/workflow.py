"""Workflow state and status models."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import numpy as np


class NumpyJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy types."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class AgentStatus(str, Enum):
    """Individual agent execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AgentResult:
    """Result from an agent execution."""
    agent_name: str
    status: AgentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    result_data: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_name": self.agent_name,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result_data": self.result_data,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentResult":
        """Create from dictionary."""
        return cls(
            agent_name=data["agent_name"],
            status=AgentStatus(data["status"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            result_data=data.get("result_data", {}),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
        )


@dataclass
class WorkflowState:
    """Complete workflow state for tracking execution."""
    workflow_id: str
    contract_id: str
    performance_year: int
    performance_month: int
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # Per-agent status tracking
    data_agent_status: AgentStatus = AgentStatus.PENDING
    validation_agent_status: AgentStatus = AgentStatus.PENDING
    analysis_agent_status: AgentStatus = AgentStatus.PENDING
    reporting_agent_status: AgentStatus = AgentStatus.PENDING

    # Stage-specific results
    extracted_files: List[str] = field(default_factory=list)
    records_extracted: Dict[str, int] = field(default_factory=dict)
    validation_passed: bool = False
    critical_errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    auto_fixes_applied: int = 0
    financial_metrics: Optional[Dict[str, Any]] = None
    quality_metrics: Optional[Dict[str, Any]] = None
    risk_metrics: Optional[Dict[str, Any]] = None
    predictions: Optional[Dict[str, Any]] = None
    reports_generated: List[str] = field(default_factory=list)

    # Error tracking
    retry_count: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)

    # Agent results history
    agent_results: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "workflow_id": self.workflow_id,
            "contract_id": self.contract_id,
            "performance_year": self.performance_year,
            "performance_month": self.performance_month,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "data_agent_status": self.data_agent_status.value,
            "validation_agent_status": self.validation_agent_status.value,
            "analysis_agent_status": self.analysis_agent_status.value,
            "reporting_agent_status": self.reporting_agent_status.value,
            "extracted_files": self.extracted_files,
            "records_extracted": self.records_extracted,
            "validation_passed": self.validation_passed,
            "critical_errors": self.critical_errors,
            "warnings": self.warnings,
            "auto_fixes_applied": self.auto_fixes_applied,
            "financial_metrics": self.financial_metrics,
            "quality_metrics": self.quality_metrics,
            "risk_metrics": self.risk_metrics,
            "predictions": self.predictions,
            "reports_generated": self.reports_generated,
            "retry_count": self.retry_count,
            "errors": self.errors,
            "agent_results": self.agent_results,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowState":
        """Create from dictionary."""
        return cls(
            workflow_id=data["workflow_id"],
            contract_id=data["contract_id"],
            performance_year=data["performance_year"],
            performance_month=data["performance_month"],
            status=WorkflowStatus(data["status"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            data_agent_status=AgentStatus(data["data_agent_status"]),
            validation_agent_status=AgentStatus(data["validation_agent_status"]),
            analysis_agent_status=AgentStatus(data["analysis_agent_status"]),
            reporting_agent_status=AgentStatus(data["reporting_agent_status"]),
            extracted_files=data.get("extracted_files", []),
            records_extracted=data.get("records_extracted", {}),
            validation_passed=data.get("validation_passed", False),
            critical_errors=data.get("critical_errors", []),
            warnings=data.get("warnings", []),
            auto_fixes_applied=data.get("auto_fixes_applied", 0),
            financial_metrics=data.get("financial_metrics"),
            quality_metrics=data.get("quality_metrics"),
            risk_metrics=data.get("risk_metrics"),
            predictions=data.get("predictions"),
            reports_generated=data.get("reports_generated", []),
            retry_count=data.get("retry_count", 0),
            errors=data.get("errors", []),
            agent_results=data.get("agent_results", []),
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), cls=NumpyJSONEncoder)

    @classmethod
    def from_json(cls, json_str: str) -> "WorkflowState":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))
