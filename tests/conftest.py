"""Pytest fixtures for the analytics pipeline tests."""
import asyncio
import os
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict

# Set test environment
os.environ["DATABASE_URL"] = "postgresql://analytics:analytics_password@localhost:5432/healthcare_analytics"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["SMTP_HOST"] = "localhost"
os.environ["SMTP_PORT"] = "1025"
os.environ["DATA_DIR"] = "/tmp/test_data"
os.environ["REPORTS_DIR"] = "/tmp/test_reports"

from src.services.database import DatabaseService
from src.services.state_manager import StateManager
from src.services.email_service import EmailService
from src.models.workflow import WorkflowState, WorkflowStatus, AgentStatus
from src.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def database():
    """Database service fixture."""
    db = DatabaseService()
    await db.connect()
    yield db
    await db.disconnect()


@pytest.fixture(scope="session")
async def state_manager():
    """State manager fixture."""
    sm = StateManager()
    await sm.connect()
    yield sm
    await sm.disconnect()


@pytest.fixture(scope="session")
def email_service():
    """Email service fixture."""
    return EmailService()


@pytest.fixture
def sample_workflow_state():
    """Create a sample workflow state for testing."""
    return WorkflowState(
        workflow_id="test-wf-001",
        contract_id="VBC-MSSP-001",
        performance_year=2024,
        performance_month=11,
        status=WorkflowStatus.PENDING,
        started_at=datetime.now(),
    )


@pytest.fixture
def sample_members_df():
    """Create sample members DataFrame."""
    today = datetime.now()
    return pd.DataFrame({
        "member_id": [f"M{str(i).zfill(8)}" for i in range(100)],
        "first_name": [f"First{i}" for i in range(100)],
        "last_name": [f"Last{i}" for i in range(100)],
        "date_of_birth": [(today - timedelta(days=365*70 + i*30)).date() for i in range(100)],
        "gender": ["M" if i % 2 == 0 else "F" for i in range(100)],
        "attribution_start_date": [(today - timedelta(days=365)).date() for _ in range(100)],
        "attribution_end_date": [None for _ in range(100)],
        "primary_pcp_id": [f"PCP{str(i % 10).zfill(4)}" for i in range(100)],
        "pcp_name": [f"Dr. Smith {i % 10}" for i in range(100)],
        "hcc_risk_score": np.random.lognormal(0, 0.5, 100).round(4),
        "risk_category": ["Low" if i < 40 else "Medium" if i < 80 else "High" for i in range(100)],
    })


@pytest.fixture
def sample_medical_claims_df(sample_members_df):
    """Create sample medical claims DataFrame."""
    member_ids = sample_members_df["member_id"].tolist()
    today = datetime.now()
    n_claims = 500

    return pd.DataFrame({
        "claim_id": [f"MC{str(i).zfill(10)}" for i in range(n_claims)],
        "member_id": [member_ids[i % len(member_ids)] for i in range(n_claims)],
        "service_date": [(today - timedelta(days=i % 300)).date() for i in range(n_claims)],
        "paid_date": [(today - timedelta(days=(i % 300) - 30)).date() for i in range(n_claims)],
        "paid_amount": np.random.lognormal(5, 1.5, n_claims).round(2),
        "allowed_amount": np.random.lognormal(5.2, 1.5, n_claims).round(2),
        "place_of_service": ["11" for _ in range(n_claims)],
        "provider_specialty": ["Internal Medicine" for _ in range(n_claims)],
        "primary_diagnosis": ["E11.9" for _ in range(n_claims)],
        "claim_status": ["PAID" for _ in range(n_claims)],
        "service_category": ["Office Visit" for _ in range(n_claims)],
        "er_visit": [i % 20 == 0 for i in range(n_claims)],
        "inpatient_admit": [i % 50 == 0 for i in range(n_claims)],
    })


@pytest.fixture
def sample_pharmacy_claims_df(sample_members_df):
    """Create sample pharmacy claims DataFrame."""
    member_ids = sample_members_df["member_id"].tolist()
    today = datetime.now()
    n_claims = 200

    return pd.DataFrame({
        "claim_id": [f"RX{str(i).zfill(10)}" for i in range(n_claims)],
        "member_id": [member_ids[i % len(member_ids)] for i in range(n_claims)],
        "fill_date": [(today - timedelta(days=i % 300)).date() for i in range(n_claims)],
        "paid_amount": np.random.lognormal(3, 1, n_claims).round(2),
        "drug_name": ["Metformin" for _ in range(n_claims)],
        "generic_indicator": [True for _ in range(n_claims)],
        "days_supply": [30 for _ in range(n_claims)],
        "therapeutic_class": ["Diabetes" for _ in range(n_claims)],
        "condition_category": ["Chronic" for _ in range(n_claims)],
    })


@pytest.fixture
def sample_quality_measures_df():
    """Create sample quality measures DataFrame."""
    return pd.DataFrame({
        "measure_id": [f"QM{str(i).zfill(3)}" for i in range(1, 24)],
        "measure_name": [f"Quality Measure {i}" for i in range(1, 24)],
        "measure_category": [
            "preventive_care" if i <= 6 else
            "chronic_disease" if i <= 12 else
            "care_coordination" if i <= 18 else
            "patient_experience"
            for i in range(1, 24)
        ],
        "numerator": [800 + i * 10 for i in range(23)],
        "denominator": [1000 for _ in range(23)],
        "exclusions": [50 for _ in range(23)],
        "performance_rate": [80 + (i % 15) for i in range(23)],
        "national_benchmark": [82 for _ in range(23)],
        "measure_weight": [1.0 if i <= 6 else 2.0 if i <= 12 else 1.5 if i <= 18 else 1.0 for i in range(1, 24)],
        "performance_year": [2024 for _ in range(23)],
        "performance_month": [11 for _ in range(23)],
    })


@pytest.fixture
def claims_with_issues(sample_medical_claims_df):
    """Create medical claims with intentional quality issues."""
    df = sample_medical_claims_df.copy()

    # Add duplicates (~2%)
    dupes = df.head(10).copy()
    df = pd.concat([df, dupes], ignore_index=True)

    # Add negative amounts (~0.5%)
    df.loc[df.index[:3], "paid_amount"] = df.loc[df.index[:3], "paid_amount"] * -1

    # Add future dates (~0.3%)
    future_date = (datetime.now() + timedelta(days=365)).date()
    df.loc[df.index[5:7], "service_date"] = future_date

    return df
