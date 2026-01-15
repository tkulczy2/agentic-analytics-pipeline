"""Financial metrics models."""
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class FinancialMetrics:
    """MSSP financial metrics calculations."""

    # Contract parameters
    baseline_spending: float = 0.0  # Annual baseline
    shared_savings_rate: float = 0.5  # 50% default
    target_reduction_pct: float = 0.05  # 5% default

    # Computed metrics
    actual_spending: float = 0.0
    medical_spending: float = 0.0
    pharmacy_spending: float = 0.0
    total_savings: float = 0.0
    savings_percentage: float = 0.0
    shared_savings_amount: float = 0.0

    # PMPM metrics
    baseline_pmpm: float = 0.0
    actual_pmpm: float = 0.0
    target_pmpm: float = 0.0

    # Utilization metrics
    member_months: int = 0
    average_members: int = 0
    total_admits: int = 0
    total_er_visits: int = 0
    admits_per_1000: float = 0.0
    er_visits_per_1000: float = 0.0

    # Period info
    performance_year: int = 0
    performance_month: int = 0

    def calculate_derived_metrics(self):
        """Calculate all derived metrics from base values."""
        if self.baseline_spending > 0:
            self.total_savings = self.baseline_spending - self.actual_spending
            self.savings_percentage = (self.total_savings / self.baseline_spending) * 100

            if self.total_savings > 0:
                self.shared_savings_amount = self.total_savings * self.shared_savings_rate
            else:
                self.shared_savings_amount = 0.0

        if self.member_months > 0:
            self.average_members = self.member_months // self.performance_month if self.performance_month > 0 else 0
            self.actual_pmpm = self.actual_spending / self.member_months

            if self.average_members > 0:
                annual_baseline_per_member = self.baseline_spending / self.average_members
                self.baseline_pmpm = annual_baseline_per_member / 12
                self.target_pmpm = self.baseline_pmpm * (1 - self.target_reduction_pct)

        # Utilization per 1000 members
        if self.average_members > 0:
            self.admits_per_1000 = (self.total_admits / self.average_members) * 1000
            self.er_visits_per_1000 = (self.total_er_visits / self.average_members) * 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "baseline_spending": self.baseline_spending,
            "shared_savings_rate": self.shared_savings_rate,
            "target_reduction_pct": self.target_reduction_pct,
            "actual_spending": self.actual_spending,
            "medical_spending": self.medical_spending,
            "pharmacy_spending": self.pharmacy_spending,
            "total_savings": self.total_savings,
            "savings_percentage": self.savings_percentage,
            "shared_savings_amount": self.shared_savings_amount,
            "baseline_pmpm": self.baseline_pmpm,
            "actual_pmpm": self.actual_pmpm,
            "target_pmpm": self.target_pmpm,
            "member_months": self.member_months,
            "average_members": self.average_members,
            "total_admits": self.total_admits,
            "total_er_visits": self.total_er_visits,
            "admits_per_1000": self.admits_per_1000,
            "er_visits_per_1000": self.er_visits_per_1000,
            "performance_year": self.performance_year,
            "performance_month": self.performance_month,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FinancialMetrics":
        """Create from dictionary."""
        metrics = cls(
            baseline_spending=data.get("baseline_spending", 0.0),
            shared_savings_rate=data.get("shared_savings_rate", 0.5),
            target_reduction_pct=data.get("target_reduction_pct", 0.05),
            actual_spending=data.get("actual_spending", 0.0),
            medical_spending=data.get("medical_spending", 0.0),
            pharmacy_spending=data.get("pharmacy_spending", 0.0),
            member_months=data.get("member_months", 0),
            average_members=data.get("average_members", 0),
            total_admits=data.get("total_admits", 0),
            total_er_visits=data.get("total_er_visits", 0),
            performance_year=data.get("performance_year", 0),
            performance_month=data.get("performance_month", 0),
        )
        metrics.calculate_derived_metrics()
        return metrics
