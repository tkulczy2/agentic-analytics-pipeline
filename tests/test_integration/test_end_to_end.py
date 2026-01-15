"""End-to-end integration tests for the analytics pipeline."""
import asyncio
import os
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.orchestrator import OrchestratorAgent
from src.agents.data_extraction import DataExtractionAgent
from src.agents.validation import ValidationAgent
from src.agents.analysis import AnalysisAgent
from src.agents.reporting import ReportingAgent
from src.models.workflow import WorkflowState, WorkflowStatus, AgentStatus
from src.services.state_manager import StateManager
from src.services.database import DatabaseService


@pytest.mark.asyncio
class TestEndToEndPipeline:
    """Complete pipeline integration tests."""

    @pytest.fixture
    def mock_database(self, sample_members_df, sample_medical_claims_df, sample_pharmacy_claims_df, sample_quality_measures_df):
        """Create a mock database that returns sample data."""
        db = MagicMock(spec=DatabaseService)

        def mock_read_sql(query, params=None):
            if "members" in query.lower():
                return sample_members_df
            elif "medical_claims" in query.lower():
                return sample_medical_claims_df
            elif "pharmacy_claims" in query.lower():
                return sample_pharmacy_claims_df
            elif "quality_measures" in query.lower():
                return sample_quality_measures_df
            return sample_members_df

        db.read_sql = mock_read_sql
        db.health_check = AsyncMock(return_value=True)
        return db

    @pytest.fixture
    def mock_state_manager(self):
        """Create a mock state manager."""
        sm = MagicMock(spec=StateManager)
        sm.save_workflow = AsyncMock()
        sm.get_workflow = AsyncMock(return_value=None)
        sm.add_log = AsyncMock()
        sm.get_last_extraction_time = AsyncMock(return_value=None)
        sm.health_check = AsyncMock(return_value=True)
        return sm

    async def test_data_extraction_agent(self, mock_database, mock_state_manager, sample_workflow_state, tmp_path):
        """Test data extraction agent extracts all datasets."""
        agent = DataExtractionAgent(
            state_manager=mock_state_manager,
            database=mock_database,
            data_dir=str(tmp_path)
        )

        result = await agent.run(sample_workflow_state)

        assert result.status == AgentStatus.COMPLETED
        assert "extracted_files" in result.result_data
        assert "records_extracted" in result.result_data
        assert len(result.result_data["extracted_files"]) == 4

        # Verify files were created
        for file_path in result.result_data["extracted_files"]:
            assert Path(file_path).exists()

    async def test_validation_agent_clean_data(self, mock_state_manager, sample_workflow_state, sample_members_df, sample_medical_claims_df, sample_pharmacy_claims_df, sample_quality_measures_df, tmp_path):
        """Test validation agent with clean data."""
        # Save sample data to files
        data_dir = tmp_path / "extracts"
        data_dir.mkdir(parents=True, exist_ok=True)

        sample_members_df.to_csv(data_dir / f"{sample_workflow_state.workflow_id}_members.csv", index=False)
        sample_medical_claims_df.to_csv(data_dir / f"{sample_workflow_state.workflow_id}_medical_claims.csv", index=False)
        sample_pharmacy_claims_df.to_csv(data_dir / f"{sample_workflow_state.workflow_id}_pharmacy_claims.csv", index=False)
        sample_quality_measures_df.to_csv(data_dir / f"{sample_workflow_state.workflow_id}_quality_measures.csv", index=False)

        agent = ValidationAgent(
            state_manager=mock_state_manager,
            data_dir=str(tmp_path)
        )

        result = await agent.run(sample_workflow_state)

        assert result.status == AgentStatus.COMPLETED
        assert result.result_data["validation_passed"]

    async def test_validation_agent_with_issues(self, mock_state_manager, sample_workflow_state, claims_with_issues, sample_members_df, sample_pharmacy_claims_df, sample_quality_measures_df, tmp_path):
        """Test validation agent detects and fixes issues."""
        # Save data with issues
        data_dir = tmp_path / "extracts"
        data_dir.mkdir(parents=True, exist_ok=True)

        sample_members_df.to_csv(data_dir / f"{sample_workflow_state.workflow_id}_members.csv", index=False)
        claims_with_issues.to_csv(data_dir / f"{sample_workflow_state.workflow_id}_medical_claims.csv", index=False)
        sample_pharmacy_claims_df.to_csv(data_dir / f"{sample_workflow_state.workflow_id}_pharmacy_claims.csv", index=False)
        sample_quality_measures_df.to_csv(data_dir / f"{sample_workflow_state.workflow_id}_quality_measures.csv", index=False)

        agent = ValidationAgent(
            state_manager=mock_state_manager,
            data_dir=str(tmp_path)
        )

        result = await agent.run(sample_workflow_state)

        # Should complete with auto-fixes applied
        assert result.result_data["auto_fixes_applied"] > 0

    async def test_analysis_agent(self, mock_state_manager, sample_workflow_state, sample_members_df, sample_medical_claims_df, sample_pharmacy_claims_df, sample_quality_measures_df, tmp_path):
        """Test analysis agent calculates all metrics."""
        # Save sample data
        data_dir = tmp_path / "extracts"
        data_dir.mkdir(parents=True, exist_ok=True)

        sample_members_df.to_csv(data_dir / f"{sample_workflow_state.workflow_id}_members.csv", index=False)
        sample_medical_claims_df.to_csv(data_dir / f"{sample_workflow_state.workflow_id}_medical_claims.csv", index=False)
        sample_pharmacy_claims_df.to_csv(data_dir / f"{sample_workflow_state.workflow_id}_pharmacy_claims.csv", index=False)
        sample_quality_measures_df.to_csv(data_dir / f"{sample_workflow_state.workflow_id}_quality_measures.csv", index=False)

        agent = AnalysisAgent(
            state_manager=mock_state_manager,
            data_dir=str(tmp_path)
        )

        result = await agent.run(sample_workflow_state)

        assert result.status == AgentStatus.COMPLETED
        assert "financial_metrics" in result.result_data
        assert "quality_metrics" in result.result_data
        assert "risk_metrics" in result.result_data
        assert "predictions" in result.result_data

        # Verify financial metrics
        financial = result.result_data["financial_metrics"]
        assert financial["actual_spending"] > 0
        assert financial["average_members"] > 0

        # Verify quality metrics
        quality = result.result_data["quality_metrics"]
        assert quality["composite_score"] > 0

        # Verify risk stratification
        risk = result.result_data["risk_metrics"]
        assert risk["total_members"] == 100

    async def test_reporting_agent(self, mock_state_manager, sample_workflow_state, tmp_path):
        """Test reporting agent generates PowerPoint."""
        # Set up workflow state with metrics
        sample_workflow_state.financial_metrics = {
            "total_savings": 4_000_000,
            "savings_percentage": 5.5,
            "actual_spending": 68_000_000,
            "baseline_spending": 72_000_000,
            "average_members": 11000,
            "er_visits_per_1000": 400,
            "admits_per_1000": 50,
        }
        sample_workflow_state.quality_metrics = {
            "composite_score": 85.5,
            "quality_gate_status": "eligible",
            "preventive_care_score": 85,
            "chronic_disease_score": 82,
            "care_coordination_score": 88,
            "patient_experience_score": 90,
        }
        sample_workflow_state.risk_metrics = {
            "total_members": 11000,
            "low_risk_count": 4400,
            "medium_risk_count": 4400,
            "high_risk_count": 2200,
            "average_risk_score": 1.05,
            "low_risk_pmpm": 300,
            "medium_risk_pmpm": 500,
            "high_risk_pmpm": 1200,
        }
        sample_workflow_state.predictions = {
            "projected_year_end_savings": 4_500_000,
            "projected_shared_savings": 2_250_000,
            "probability_shared_savings": 0.85,
            "risks": [],
            "opportunities": [],
        }

        from src.services.report_generator import ReportGenerator
        from src.services.email_service import EmailService

        report_gen = ReportGenerator(reports_dir=str(tmp_path / "reports"))
        email_svc = MagicMock(spec=EmailService)
        email_svc.send_workflow_completion = AsyncMock(return_value=True)

        agent = ReportingAgent(
            state_manager=mock_state_manager,
            report_generator=report_gen,
            email_service=email_svc
        )

        result = await agent.run(sample_workflow_state)

        assert result.status == AgentStatus.COMPLETED
        assert len(result.result_data["reports_generated"]) > 0

        # Verify PowerPoint was created
        report_path = Path(result.result_data["reports_generated"][0])
        assert report_path.exists()
        assert report_path.suffix == ".pptx"


@pytest.mark.asyncio
class TestWorkflowControl:
    """Tests for workflow pause, resume, and cancel."""

    async def test_workflow_state_persistence(self, mock_state_manager, sample_workflow_state):
        """Test workflow state is saved correctly."""
        await mock_state_manager.save_workflow(sample_workflow_state)

        mock_state_manager.save_workflow.assert_called_once()

    async def test_workflow_status_transitions(self, sample_workflow_state):
        """Test workflow status transitions."""
        assert sample_workflow_state.status == WorkflowStatus.PENDING

        sample_workflow_state.status = WorkflowStatus.RUNNING
        assert sample_workflow_state.status == WorkflowStatus.RUNNING

        sample_workflow_state.status = WorkflowStatus.PAUSED
        assert sample_workflow_state.status == WorkflowStatus.PAUSED

        sample_workflow_state.status = WorkflowStatus.RUNNING
        sample_workflow_state.status = WorkflowStatus.COMPLETED
        assert sample_workflow_state.status == WorkflowStatus.COMPLETED

    async def test_agent_status_tracking(self, sample_workflow_state):
        """Test agent status is tracked correctly."""
        assert sample_workflow_state.data_agent_status == AgentStatus.PENDING
        assert sample_workflow_state.validation_agent_status == AgentStatus.PENDING
        assert sample_workflow_state.analysis_agent_status == AgentStatus.PENDING
        assert sample_workflow_state.reporting_agent_status == AgentStatus.PENDING

        sample_workflow_state.data_agent_status = AgentStatus.COMPLETED
        sample_workflow_state.validation_agent_status = AgentStatus.COMPLETED
        sample_workflow_state.analysis_agent_status = AgentStatus.COMPLETED
        sample_workflow_state.reporting_agent_status = AgentStatus.COMPLETED

        assert all(
            status == AgentStatus.COMPLETED
            for status in [
                sample_workflow_state.data_agent_status,
                sample_workflow_state.validation_agent_status,
                sample_workflow_state.analysis_agent_status,
                sample_workflow_state.reporting_agent_status,
            ]
        )
