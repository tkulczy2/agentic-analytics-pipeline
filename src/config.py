"""Configuration management for the analytics pipeline."""
import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(
        default="postgresql://analytics:analytics_password@localhost:5432/healthcare_analytics",
        alias="DATABASE_URL"
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL"
    )

    # SMTP
    smtp_host: str = Field(default="localhost", alias="SMTP_HOST")
    smtp_port: int = Field(default=1025, alias="SMTP_PORT")

    # Paths
    data_dir: str = Field(default="/app/data", alias="DATA_DIR")
    reports_dir: str = Field(default="/app/reports", alias="REPORTS_DIR")

    # Workflow settings
    max_retries: int = 3
    retry_delay_base: float = 2.0  # Exponential backoff base in seconds

    # Contract defaults (for demo)
    default_contract_id: str = "VBC-MSSP-001"
    baseline_spending: float = 72_000_000.0  # $72M annual
    shared_savings_rate: float = 0.50  # 50%
    target_reduction_pct: float = 0.05  # 5%
    quality_threshold: float = 80.0  # 80%

    class Config:
        env_file = ".env"
        extra = "ignore"


# Global settings instance
settings = Settings()
