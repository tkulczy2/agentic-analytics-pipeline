"""Risk stratification models."""
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class RiskStratification:
    """HCC risk stratification calculations."""

    # Risk score thresholds
    LOW_RISK_MAX = 0.8
    HIGH_RISK_MIN = 1.5

    # Counts by category
    low_risk_count: int = 0
    medium_risk_count: int = 0
    high_risk_count: int = 0
    total_members: int = 0

    # PMPM by category
    low_risk_pmpm: float = 0.0
    medium_risk_pmpm: float = 0.0
    high_risk_pmpm: float = 0.0

    # Spending by category
    low_risk_spending: float = 0.0
    medium_risk_spending: float = 0.0
    high_risk_spending: float = 0.0

    # Average risk score
    average_risk_score: float = 0.0

    # Period info
    performance_year: int = 0
    performance_month: int = 0

    @classmethod
    def categorize_risk(cls, score: float) -> str:
        """Categorize a risk score."""
        if score < cls.LOW_RISK_MAX:
            return "Low"
        elif score > cls.HIGH_RISK_MIN:
            return "High"
        else:
            return "Medium"

    def calculate_percentages(self) -> Dict[str, float]:
        """Calculate percentage distribution by risk category."""
        if self.total_members == 0:
            return {"low": 0.0, "medium": 0.0, "high": 0.0}

        return {
            "low": (self.low_risk_count / self.total_members) * 100,
            "medium": (self.medium_risk_count / self.total_members) * 100,
            "high": (self.high_risk_count / self.total_members) * 100,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        percentages = self.calculate_percentages()
        return {
            "low_risk_count": self.low_risk_count,
            "medium_risk_count": self.medium_risk_count,
            "high_risk_count": self.high_risk_count,
            "total_members": self.total_members,
            "low_risk_pmpm": self.low_risk_pmpm,
            "medium_risk_pmpm": self.medium_risk_pmpm,
            "high_risk_pmpm": self.high_risk_pmpm,
            "low_risk_spending": self.low_risk_spending,
            "medium_risk_spending": self.medium_risk_spending,
            "high_risk_spending": self.high_risk_spending,
            "average_risk_score": self.average_risk_score,
            "low_risk_pct": percentages["low"],
            "medium_risk_pct": percentages["medium"],
            "high_risk_pct": percentages["high"],
            "performance_year": self.performance_year,
            "performance_month": self.performance_month,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskStratification":
        """Create from dictionary."""
        return cls(
            low_risk_count=data.get("low_risk_count", 0),
            medium_risk_count=data.get("medium_risk_count", 0),
            high_risk_count=data.get("high_risk_count", 0),
            total_members=data.get("total_members", 0),
            low_risk_pmpm=data.get("low_risk_pmpm", 0.0),
            medium_risk_pmpm=data.get("medium_risk_pmpm", 0.0),
            high_risk_pmpm=data.get("high_risk_pmpm", 0.0),
            low_risk_spending=data.get("low_risk_spending", 0.0),
            medium_risk_spending=data.get("medium_risk_spending", 0.0),
            high_risk_spending=data.get("high_risk_spending", 0.0),
            average_risk_score=data.get("average_risk_score", 0.0),
            performance_year=data.get("performance_year", 0),
            performance_month=data.get("performance_month", 0),
        )
