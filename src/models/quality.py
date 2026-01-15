"""Quality metrics models."""
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class QualityMetrics:
    """MSSP quality score calculations."""

    # Category weights
    MEASURE_WEIGHTS = {
        'preventive_care': 1.0,
        'chronic_disease': 2.0,
        'care_coordination': 1.5,
        'patient_experience': 1.0
    }

    # Computed scores
    composite_score: float = 0.0
    quality_threshold: float = 80.0
    quality_gate_status: str = "pending"  # eligible, ineligible, at_risk

    # Per-category scores
    preventive_care_score: float = 0.0
    chronic_disease_score: float = 0.0
    care_coordination_score: float = 0.0
    patient_experience_score: float = 0.0

    # Detail measures
    measures: List[Dict[str, Any]] = field(default_factory=list)

    # Period info
    performance_year: int = 0
    performance_month: int = 0

    def calculate_composite_score(self):
        """Calculate weighted composite quality score."""
        scores = {
            'preventive_care': self.preventive_care_score,
            'chronic_disease': self.chronic_disease_score,
            'care_coordination': self.care_coordination_score,
            'patient_experience': self.patient_experience_score,
        }

        total_weight = 0.0
        weighted_sum = 0.0

        for category, score in scores.items():
            weight = self.MEASURE_WEIGHTS.get(category, 1.0)
            weighted_sum += score * weight
            total_weight += weight

        if total_weight > 0:
            self.composite_score = weighted_sum / total_weight

        # Determine quality gate status
        if self.composite_score >= self.quality_threshold:
            self.quality_gate_status = "eligible"
        elif self.composite_score >= (self.quality_threshold - 5):
            self.quality_gate_status = "at_risk"
        else:
            self.quality_gate_status = "ineligible"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "composite_score": self.composite_score,
            "quality_threshold": self.quality_threshold,
            "quality_gate_status": self.quality_gate_status,
            "preventive_care_score": self.preventive_care_score,
            "chronic_disease_score": self.chronic_disease_score,
            "care_coordination_score": self.care_coordination_score,
            "patient_experience_score": self.patient_experience_score,
            "measures": self.measures,
            "performance_year": self.performance_year,
            "performance_month": self.performance_month,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QualityMetrics":
        """Create from dictionary."""
        metrics = cls(
            composite_score=data.get("composite_score", 0.0),
            quality_threshold=data.get("quality_threshold", 80.0),
            quality_gate_status=data.get("quality_gate_status", "pending"),
            preventive_care_score=data.get("preventive_care_score", 0.0),
            chronic_disease_score=data.get("chronic_disease_score", 0.0),
            care_coordination_score=data.get("care_coordination_score", 0.0),
            patient_experience_score=data.get("patient_experience_score", 0.0),
            measures=data.get("measures", []),
            performance_year=data.get("performance_year", 0),
            performance_month=data.get("performance_month", 0),
        )
        return metrics
