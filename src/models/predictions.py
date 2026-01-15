"""Prediction models for year-end projections."""
from dataclasses import dataclass, field
from typing import Any, Dict, List
import scipy.stats as stats


@dataclass
class Predictions:
    """Predictive analytics for MSSP contracts."""

    # Year-end projections
    projected_year_end_spending: float = 0.0
    projected_year_end_savings: float = 0.0
    projected_savings_percentage: float = 0.0
    projected_shared_savings: float = 0.0

    # Probability calculations
    probability_meeting_target: float = 0.0
    probability_shared_savings: float = 0.0

    # Quality projections
    projected_quality_score: float = 0.0
    probability_quality_gate: float = 0.0

    # Confidence intervals
    savings_lower_bound: float = 0.0
    savings_upper_bound: float = 0.0

    # Risks and opportunities
    risks: List[Dict[str, Any]] = field(default_factory=list)
    opportunities: List[Dict[str, Any]] = field(default_factory=list)

    # Period info
    current_month: int = 0
    performance_year: int = 0

    @staticmethod
    def project_year_end(
        current_month: int,
        ytd_spending: float,
        baseline_spending: float,
        std_dev_pct: float = 0.10
    ) -> Dict[str, float]:
        """
        Project year-end spending with seasonal adjustment.

        Args:
            current_month: Current performance month (1-12)
            ytd_spending: Year-to-date actual spending
            baseline_spending: Annual baseline spending
            std_dev_pct: Standard deviation as percentage of baseline

        Returns:
            Dictionary with projections and confidence intervals
        """
        if current_month <= 0:
            return {}

        # Calculate monthly average
        monthly_avg = ytd_spending / current_month

        # Project remaining months with seasonal adjustment (December +10%)
        months_remaining = 12 - current_month

        projected_remaining = 0.0
        for month in range(current_month + 1, 13):
            if month == 12:
                projected_remaining += monthly_avg * 1.10  # December adjustment
            else:
                projected_remaining += monthly_avg

        projected_year_end = ytd_spending + projected_remaining
        projected_savings = baseline_spending - projected_year_end

        # Calculate confidence intervals (95%)
        std_dev = baseline_spending * std_dev_pct
        margin = 1.96 * std_dev

        return {
            "projected_spending": projected_year_end,
            "projected_savings": projected_savings,
            "savings_lower_bound": projected_savings - margin,
            "savings_upper_bound": projected_savings + margin,
        }

    @staticmethod
    def calculate_probability(
        current_value: float,
        threshold: float,
        std_dev: float
    ) -> float:
        """
        Calculate probability of exceeding threshold using normal distribution.

        Args:
            current_value: Current or projected value
            threshold: Target threshold
            std_dev: Standard deviation

        Returns:
            Probability (0-1) of meeting/exceeding threshold
        """
        if std_dev <= 0:
            return 1.0 if current_value >= threshold else 0.0

        z_score = (current_value - threshold) / std_dev
        return float(stats.norm.cdf(z_score))

    def identify_risks_and_opportunities(
        self,
        financial_metrics: Dict[str, Any],
        quality_metrics: Dict[str, Any],
        risk_metrics: Dict[str, Any]
    ):
        """Analyze current data to identify risks and opportunities."""
        self.risks = []
        self.opportunities = []

        # Check spending trend
        if financial_metrics.get("savings_percentage", 0) < 0:
            self.risks.append({
                "type": "financial",
                "severity": "high",
                "title": "Spending Over Baseline",
                "description": f"Current spending is {abs(financial_metrics.get('savings_percentage', 0)):.1f}% over baseline",
                "impact": "Potential loss of shared savings opportunity",
                "recommendation": "Review high-cost cases and implement utilization management"
            })
        elif financial_metrics.get("savings_percentage", 0) > 5:
            self.opportunities.append({
                "type": "financial",
                "severity": "positive",
                "title": "Strong Savings Performance",
                "description": f"Tracking {financial_metrics.get('savings_percentage', 0):.1f}% below baseline",
                "impact": f"Projected shared savings of ${financial_metrics.get('shared_savings_amount', 0):,.0f}",
                "recommendation": "Maintain current care management initiatives"
            })

        # Check ER utilization
        if financial_metrics.get("er_visits_per_1000", 0) > 400:
            self.risks.append({
                "type": "utilization",
                "severity": "medium",
                "title": "High ER Utilization",
                "description": f"ER visits at {financial_metrics.get('er_visits_per_1000', 0):.0f} per 1,000 members",
                "impact": "Increased costs and potential quality gaps",
                "recommendation": "Expand urgent care access and patient education"
            })

        # Check quality gate
        quality_score = quality_metrics.get("composite_score", 0)
        if quality_score < 80:
            severity = "high" if quality_score < 75 else "medium"
            self.risks.append({
                "type": "quality",
                "severity": severity,
                "title": "Quality Gate at Risk",
                "description": f"Composite score of {quality_score:.1f}% below 80% threshold",
                "impact": "May not qualify for shared savings distribution",
                "recommendation": "Focus on chronic disease and care coordination measures"
            })

        # Check high-risk member concentration
        high_risk_pct = risk_metrics.get("high_risk_pct", 0)
        if high_risk_pct > 25:
            self.risks.append({
                "type": "risk",
                "severity": "medium",
                "title": "High-Risk Population Concentration",
                "description": f"{high_risk_pct:.1f}% of members are high-risk",
                "impact": "May drive disproportionate spending",
                "recommendation": "Implement care management programs for high-risk members"
            })

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "projected_year_end_spending": self.projected_year_end_spending,
            "projected_year_end_savings": self.projected_year_end_savings,
            "projected_savings_percentage": self.projected_savings_percentage,
            "projected_shared_savings": self.projected_shared_savings,
            "probability_meeting_target": self.probability_meeting_target,
            "probability_shared_savings": self.probability_shared_savings,
            "projected_quality_score": self.projected_quality_score,
            "probability_quality_gate": self.probability_quality_gate,
            "savings_lower_bound": self.savings_lower_bound,
            "savings_upper_bound": self.savings_upper_bound,
            "risks": self.risks,
            "opportunities": self.opportunities,
            "current_month": self.current_month,
            "performance_year": self.performance_year,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Predictions":
        """Create from dictionary."""
        return cls(
            projected_year_end_spending=data.get("projected_year_end_spending", 0.0),
            projected_year_end_savings=data.get("projected_year_end_savings", 0.0),
            projected_savings_percentage=data.get("projected_savings_percentage", 0.0),
            projected_shared_savings=data.get("projected_shared_savings", 0.0),
            probability_meeting_target=data.get("probability_meeting_target", 0.0),
            probability_shared_savings=data.get("probability_shared_savings", 0.0),
            projected_quality_score=data.get("projected_quality_score", 0.0),
            probability_quality_gate=data.get("probability_quality_gate", 0.0),
            savings_lower_bound=data.get("savings_lower_bound", 0.0),
            savings_upper_bound=data.get("savings_upper_bound", 0.0),
            risks=data.get("risks", []),
            opportunities=data.get("opportunities", []),
            current_month=data.get("current_month", 0),
            performance_year=data.get("performance_year", 0),
        )
