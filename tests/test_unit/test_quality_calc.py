"""Unit tests for quality score calculations."""
import pytest
from src.models.quality import QualityMetrics


class TestQualityMetrics:
    """Tests for QualityMetrics calculations."""

    def test_calculate_composite_score_eligible(self):
        """Test composite score when eligible for quality gate."""
        metrics = QualityMetrics(
            preventive_care_score=85.0,
            chronic_disease_score=82.0,
            care_coordination_score=88.0,
            patient_experience_score=90.0,
            quality_threshold=80.0,
        )

        metrics.calculate_composite_score()

        # Weighted average: (85*1 + 82*2 + 88*1.5 + 90*1) / (1 + 2 + 1.5 + 1)
        # = (85 + 164 + 132 + 90) / 5.5 = 471 / 5.5 = 85.64
        assert metrics.composite_score == pytest.approx(85.64, rel=0.01)
        assert metrics.quality_gate_status == "eligible"

    def test_calculate_composite_score_at_risk(self):
        """Test composite score when at risk for quality gate."""
        metrics = QualityMetrics(
            preventive_care_score=78.0,
            chronic_disease_score=76.0,
            care_coordination_score=80.0,
            patient_experience_score=82.0,
            quality_threshold=80.0,
        )

        metrics.calculate_composite_score()

        # Weighted average should be around 78, which is within 5% of 80
        assert metrics.composite_score < 80
        assert metrics.composite_score >= 75
        assert metrics.quality_gate_status == "at_risk"

    def test_calculate_composite_score_ineligible(self):
        """Test composite score when ineligible for quality gate."""
        metrics = QualityMetrics(
            preventive_care_score=70.0,
            chronic_disease_score=68.0,
            care_coordination_score=72.0,
            patient_experience_score=74.0,
            quality_threshold=80.0,
        )

        metrics.calculate_composite_score()

        # Score should be well below threshold
        assert metrics.composite_score < 75
        assert metrics.quality_gate_status == "ineligible"

    def test_chronic_disease_weight(self):
        """Test that chronic disease has higher weight (2.0x)."""
        # When chronic disease is high and others are low
        metrics_high_chronic = QualityMetrics(
            preventive_care_score=50.0,
            chronic_disease_score=95.0,  # High
            care_coordination_score=50.0,
            patient_experience_score=50.0,
        )
        metrics_high_chronic.calculate_composite_score()

        # When preventive is high and others are low
        metrics_high_preventive = QualityMetrics(
            preventive_care_score=95.0,  # High
            chronic_disease_score=50.0,
            care_coordination_score=50.0,
            patient_experience_score=50.0,
        )
        metrics_high_preventive.calculate_composite_score()

        # Chronic disease should have more impact
        assert metrics_high_chronic.composite_score > metrics_high_preventive.composite_score

    def test_to_dict(self):
        """Test dictionary serialization."""
        metrics = QualityMetrics(
            composite_score=85.0,
            quality_gate_status="eligible",
            preventive_care_score=85.0,
            chronic_disease_score=82.0,
            performance_year=2024,
        )

        data = metrics.to_dict()

        assert data["composite_score"] == 85.0
        assert data["quality_gate_status"] == "eligible"
        assert data["performance_year"] == 2024

    def test_from_dict(self):
        """Test dictionary deserialization."""
        data = {
            "composite_score": 85.0,
            "quality_threshold": 80.0,
            "quality_gate_status": "eligible",
            "preventive_care_score": 85.0,
            "chronic_disease_score": 82.0,
            "care_coordination_score": 88.0,
            "patient_experience_score": 90.0,
            "measures": [],
            "performance_year": 2024,
            "performance_month": 11,
        }

        metrics = QualityMetrics.from_dict(data)

        assert metrics.composite_score == 85.0
        assert metrics.quality_gate_status == "eligible"
