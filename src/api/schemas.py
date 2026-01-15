"""Pydantic schemas for API request/response models."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorkflowCreate(BaseModel):
    """Request body for creating a new workflow."""
    contract_id: str = Field(..., description="Contract identifier")
    performance_year: int = Field(..., ge=2020, le=2030, description="Performance year")
    performance_month: int = Field(..., ge=1, le=12, description="Performance month")


class WorkflowResponse(BaseModel):
    """Response model for workflow operations."""
    workflow_id: str
    contract_id: str
    performance_year: int
    performance_month: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Agent statuses
    data_agent_status: str
    validation_agent_status: str
    analysis_agent_status: str
    reporting_agent_status: str

    # Results
    extracted_files: List[str] = []
    records_extracted: Dict[str, int] = {}
    validation_passed: bool = False
    critical_errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    auto_fixes_applied: int = 0
    financial_metrics: Optional[Dict[str, Any]] = None
    quality_metrics: Optional[Dict[str, Any]] = None
    risk_metrics: Optional[Dict[str, Any]] = None
    predictions: Optional[Dict[str, Any]] = None
    reports_generated: List[str] = []

    # Error tracking
    retry_count: int = 0
    errors: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


class LogEntry(BaseModel):
    """Log entry model."""
    timestamp: datetime
    level: str
    message: str
    data: Dict[str, Any] = {}


class LogsResponse(BaseModel):
    """Response model for workflow logs."""
    workflow_id: str
    logs: List[LogEntry]


class TestDataConfig(BaseModel):
    """Configuration for test data generation."""
    num_members: int = Field(default=12000, ge=100, le=100000)
    num_medical_claims: int = Field(default=50000, ge=1000, le=500000)
    num_pharmacy_claims: int = Field(default=15000, ge=500, le=100000)
    num_quality_measures: int = Field(default=23, ge=10, le=50)
    include_duplicates: bool = Field(default=True, description="Add ~2% duplicate claims")
    include_negative_amounts: bool = Field(default=True, description="Add ~0.5% negative amounts")
    include_future_dates: bool = Field(default=True, description="Add ~0.3% dates with year+1 typo")
    include_gender_mismatch: bool = Field(default=True, description="Add 5 male patients with pregnancy codes")
    include_high_cost_outliers: bool = Field(default=True, description="Add 3 claims > $500K")


class TestDataResponse(BaseModel):
    """Response model for test data generation."""
    success: bool
    message: str
    records_created: Dict[str, int]


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    database: bool
    redis: bool
    smtp: bool
    timestamp: datetime
