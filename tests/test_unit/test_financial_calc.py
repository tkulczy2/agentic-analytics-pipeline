"""Unit tests for financial calculations."""
import pytest
from src.models.financial import FinancialMetrics


class TestFinancialMetrics:
    """Tests for FinancialMetrics calculations."""

    def test_calculate_derived_metrics_with_savings(self):
        """Test financial calculations when there are savings."""
        metrics = FinancialMetrics(
            baseline_spending=72_000_000,
            shared_savings_rate=0.50,
            target_reduction_pct=0.05,
            actual_spending=68_000_000,
            member_months=132_000,  # 11,000 members * 12 months
            performance_year=2024,
            performance_month=12,
        )

        metrics.calculate_derived_metrics()

        # Check savings calculations
        assert metrics.total_savings == 4_000_000
        assert metrics.savings_percentage == pytest.approx(5.56, rel=0.01)
        assert metrics.shared_savings_amount == 2_000_000

        # Check PMPM calculations
        assert metrics.average_members == 11_000
        assert metrics.actual_pmpm == pytest.approx(515.15, rel=0.01)

    def test_calculate_derived_metrics_with_loss(self):
        """Test financial calculations when spending exceeds baseline."""
        metrics = FinancialMetrics(
            baseline_spending=72_000_000,
            shared_savings_rate=0.50,
            actual_spending=75_000_000,
            member_months=132_000,
            performance_year=2024,
            performance_month=12,
        )

        metrics.calculate_derived_metrics()

        # Should show negative savings (loss)
        assert metrics.total_savings == -3_000_000
        assert metrics.savings_percentage == pytest.approx(-4.17, rel=0.01)
        assert metrics.shared_savings_amount == 0  # No shared savings when over baseline

    def test_utilization_per_1000(self):
        """Test utilization rate calculations."""
        metrics = FinancialMetrics(
            baseline_spending=72_000_000,
            actual_spending=68_000_000,
            member_months=132_000,
            total_admits=550,
            total_er_visits=4400,
            performance_year=2024,
            performance_month=12,
        )

        metrics.calculate_derived_metrics()

        # 550 admits / 11,000 members * 1000 = 50 per 1000
        assert metrics.admits_per_1000 == 50
        # 4400 ER visits / 11,000 members * 1000 = 400 per 1000
        assert metrics.er_visits_per_1000 == 400

    def test_to_dict(self):
        """Test dictionary serialization."""
        metrics = FinancialMetrics(
            baseline_spending=72_000_000,
            actual_spending=68_000_000,
            performance_year=2024,
            performance_month=11,
        )

        data = metrics.to_dict()

        assert data["baseline_spending"] == 72_000_000
        assert data["actual_spending"] == 68_000_000
        assert data["performance_year"] == 2024
        assert "total_savings" in data

    def test_from_dict(self):
        """Test dictionary deserialization."""
        data = {
            "baseline_spending": 72_000_000,
            "actual_spending": 68_000_000,
            "member_months": 132_000,
            "performance_year": 2024,
            "performance_month": 12,
        }

        metrics = FinancialMetrics.from_dict(data)

        assert metrics.baseline_spending == 72_000_000
        assert metrics.total_savings == 4_000_000  # Calculated
