"""Validation rules for healthcare data quality checks."""
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np


class ValidationSeverity(str, Enum):
    """Severity level of validation issues."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of a validation rule check."""
    rule_name: str
    category: str
    severity: ValidationSeverity
    passed: bool
    message: str
    affected_records: int = 0
    total_records: int = 0
    affected_percentage: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    auto_fixable: bool = False
    fix_applied: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_name": self.rule_name,
            "category": self.category,
            "severity": self.severity.value,
            "passed": self.passed,
            "message": self.message,
            "affected_records": self.affected_records,
            "total_records": self.total_records,
            "affected_percentage": self.affected_percentage,
            "details": self.details,
            "auto_fixable": self.auto_fixable,
            "fix_applied": self.fix_applied,
        }


class ValidationRule:
    """Base class for validation rules."""

    def __init__(
        self,
        name: str,
        category: str,
        severity: ValidationSeverity,
        auto_fixable: bool = False
    ):
        self.name = name
        self.category = category
        self.severity = severity
        self.auto_fixable = auto_fixable

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        """Run the validation rule. Override in subclasses."""
        raise NotImplementedError


class RequiredFieldsRule(ValidationRule):
    """Check that required fields are present."""

    def __init__(self, required_fields: List[str]):
        super().__init__(
            name="required_fields",
            category="completeness",
            severity=ValidationSeverity.CRITICAL,
            auto_fixable=False
        )
        self.required_fields = required_fields

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        missing = [f for f in self.required_fields if f not in df.columns]

        if missing:
            return ValidationResult(
                rule_name=self.name,
                category=self.category,
                severity=self.severity,
                passed=False,
                message=f"Missing required fields: {', '.join(missing)}",
                affected_records=len(df),
                total_records=len(df),
                affected_percentage=100.0,
                details={"missing_fields": missing},
                auto_fixable=False,
            )

        return ValidationResult(
            rule_name=self.name,
            category=self.category,
            severity=self.severity,
            passed=True,
            message="All required fields present",
            total_records=len(df),
        )


class NullValueRule(ValidationRule):
    """Check null values in specified fields."""

    def __init__(self, fields: List[str], critical_threshold: float = 0.05):
        super().__init__(
            name="null_values",
            category="completeness",
            severity=ValidationSeverity.WARNING,  # Will upgrade if > threshold
            auto_fixable=False
        )
        self.fields = fields
        self.critical_threshold = critical_threshold

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        null_counts = {}
        total_nulls = 0

        for field in self.fields:
            if field in df.columns:
                null_count = df[field].isna().sum()
                if null_count > 0:
                    null_counts[field] = int(null_count)
                    total_nulls += null_count

        if not null_counts:
            return ValidationResult(
                rule_name=self.name,
                category=self.category,
                severity=self.severity,
                passed=True,
                message="No null values in required fields",
                total_records=len(df),
            )

        max_null_pct = max(null_counts.values()) / len(df) if len(df) > 0 else 0

        severity = (
            ValidationSeverity.CRITICAL if max_null_pct > self.critical_threshold
            else ValidationSeverity.WARNING
        )

        return ValidationResult(
            rule_name=self.name,
            category=self.category,
            severity=severity,
            passed=max_null_pct <= self.critical_threshold,
            message=f"Found null values in {len(null_counts)} fields",
            affected_records=total_nulls,
            total_records=len(df),
            affected_percentage=max_null_pct * 100,
            details={"null_counts": null_counts},
            auto_fixable=False,
        )


class AgeRangeRule(ValidationRule):
    """Check age is within valid range (0-120)."""

    def __init__(self, dob_field: str = "date_of_birth"):
        super().__init__(
            name="age_range",
            category="range",
            severity=ValidationSeverity.CRITICAL,
            auto_fixable=False
        )
        self.dob_field = dob_field

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        if self.dob_field not in df.columns:
            return ValidationResult(
                rule_name=self.name,
                category=self.category,
                severity=ValidationSeverity.INFO,
                passed=True,
                message=f"Field {self.dob_field} not present, skipping",
                total_records=len(df),
            )

        today = pd.Timestamp.now()
        dob = pd.to_datetime(df[self.dob_field], errors='coerce')
        ages = (today - dob).dt.days / 365.25

        invalid_mask = (ages < 0) | (ages > 120)
        invalid_count = invalid_mask.sum()

        if invalid_count == 0:
            return ValidationResult(
                rule_name=self.name,
                category=self.category,
                severity=self.severity,
                passed=True,
                message="All ages within valid range",
                total_records=len(df),
            )

        return ValidationResult(
            rule_name=self.name,
            category=self.category,
            severity=self.severity,
            passed=False,
            message=f"{invalid_count} records with invalid age",
            affected_records=int(invalid_count),
            total_records=len(df),
            affected_percentage=invalid_count / len(df) * 100,
            auto_fixable=False,
        )


class CostAmountRule(ValidationRule):
    """Flag high-cost outliers and check for negative amounts."""

    def __init__(
        self,
        amount_fields: List[str],
        high_cost_threshold: float = 500000,
        negative_auto_fix_threshold: float = 0.01
    ):
        super().__init__(
            name="cost_amounts",
            category="range",
            severity=ValidationSeverity.WARNING,
            auto_fixable=True
        )
        self.amount_fields = amount_fields
        self.high_cost_threshold = high_cost_threshold
        self.negative_auto_fix_threshold = negative_auto_fix_threshold

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        issues = {}
        total_issues = 0

        for field in self.amount_fields:
            if field not in df.columns:
                continue

            # High cost outliers
            high_cost_count = (df[field] > self.high_cost_threshold).sum()
            if high_cost_count > 0:
                issues[f"{field}_high_cost"] = int(high_cost_count)
                total_issues += high_cost_count

            # Negative amounts
            negative_count = (df[field] < 0).sum()
            if negative_count > 0:
                issues[f"{field}_negative"] = int(negative_count)
                total_issues += negative_count

        if not issues:
            return ValidationResult(
                rule_name=self.name,
                category=self.category,
                severity=self.severity,
                passed=True,
                message="All cost amounts within expected ranges",
                total_records=len(df),
            )

        # Check if negatives are auto-fixable
        total_negatives = sum(v for k, v in issues.items() if "negative" in k)
        negative_pct = total_negatives / len(df) if len(df) > 0 else 0
        auto_fixable = negative_pct <= self.negative_auto_fix_threshold and total_negatives > 0

        return ValidationResult(
            rule_name=self.name,
            category=self.category,
            severity=self.severity,
            passed=False,
            message=f"Found {total_issues} cost amount issues",
            affected_records=total_issues,
            total_records=len(df),
            affected_percentage=total_issues / len(df) * 100 if len(df) > 0 else 0,
            details=issues,
            auto_fixable=auto_fixable,
        )


class DateLogicRule(ValidationRule):
    """Check date logic (service date before paid date, no future dates)."""

    def __init__(
        self,
        service_date_field: str = "service_date",
        paid_date_field: str = "paid_date"
    ):
        super().__init__(
            name="date_logic",
            category="logic",
            severity=ValidationSeverity.CRITICAL,
            auto_fixable=True
        )
        self.service_date_field = service_date_field
        self.paid_date_field = paid_date_field

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        issues = {}

        today = pd.Timestamp.now().normalize()

        # Check service date after paid date
        if self.service_date_field in df.columns and self.paid_date_field in df.columns:
            service = pd.to_datetime(df[self.service_date_field], errors='coerce')
            paid = pd.to_datetime(df[self.paid_date_field], errors='coerce')

            invalid_order = (service > paid) & service.notna() & paid.notna()
            invalid_count = invalid_order.sum()
            if invalid_count > 0:
                issues["service_after_paid"] = int(invalid_count)

        # Check future dates
        if self.service_date_field in df.columns:
            service = pd.to_datetime(df[self.service_date_field], errors='coerce')
            future_dates = service > today
            future_count = future_dates.sum()
            if future_count > 0:
                issues["future_service_dates"] = int(future_count)

                # Check if it's a year typo pattern (80%+ exactly 1 year ahead)
                one_year_ahead = (service.dt.year == today.year + 1) & (service > today)
                one_year_count = one_year_ahead.sum()
                if one_year_count / future_count > 0.8:
                    issues["year_typo_pattern"] = True

        if not issues:
            return ValidationResult(
                rule_name=self.name,
                category=self.category,
                severity=self.severity,
                passed=True,
                message="Date logic checks passed",
                total_records=len(df),
            )

        total_issues = sum(v for k, v in issues.items() if isinstance(v, int))
        auto_fixable = issues.get("year_typo_pattern", False)

        return ValidationResult(
            rule_name=self.name,
            category=self.category,
            severity=self.severity,
            passed=False,
            message=f"Found {total_issues} date logic issues",
            affected_records=total_issues,
            total_records=len(df),
            affected_percentage=total_issues / len(df) * 100 if len(df) > 0 else 0,
            details=issues,
            auto_fixable=auto_fixable,
        )


class DuplicateRule(ValidationRule):
    """Check for duplicate records."""

    def __init__(self, key_fields: List[str], critical_threshold: float = 0.05):
        super().__init__(
            name="duplicates",
            category="consistency",
            severity=ValidationSeverity.WARNING,
            auto_fixable=True
        )
        self.key_fields = key_fields
        self.critical_threshold = critical_threshold

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        available_keys = [f for f in self.key_fields if f in df.columns]
        if not available_keys:
            return ValidationResult(
                rule_name=self.name,
                category=self.category,
                severity=ValidationSeverity.INFO,
                passed=True,
                message="No key fields available for duplicate check",
                total_records=len(df),
            )

        duplicates = df.duplicated(subset=available_keys, keep=False)
        dup_count = duplicates.sum()

        if dup_count == 0:
            return ValidationResult(
                rule_name=self.name,
                category=self.category,
                severity=self.severity,
                passed=True,
                message="No duplicate records found",
                total_records=len(df),
            )

        dup_pct = dup_count / len(df) if len(df) > 0 else 0
        severity = (
            ValidationSeverity.CRITICAL if dup_pct > self.critical_threshold
            else ValidationSeverity.WARNING
        )
        auto_fixable = dup_pct <= self.critical_threshold

        return ValidationResult(
            rule_name=self.name,
            category=self.category,
            severity=severity,
            passed=False,
            message=f"Found {dup_count} duplicate records ({dup_pct*100:.2f}%)",
            affected_records=int(dup_count),
            total_records=len(df),
            affected_percentage=dup_pct * 100,
            details={"key_fields": available_keys},
            auto_fixable=auto_fixable,
        )


class GenderDiagnosisRule(ValidationRule):
    """Check gender-diagnosis consistency (e.g., male with pregnancy code)."""

    FEMALE_ONLY_DIAGNOSES = ["Z34", "O"]  # Pregnancy codes start with these

    def __init__(
        self,
        gender_field: str = "gender",
        diagnosis_field: str = "primary_diagnosis",
        auto_fix_threshold: int = 10
    ):
        super().__init__(
            name="gender_diagnosis",
            category="logic",
            severity=ValidationSeverity.CRITICAL,
            auto_fixable=True
        )
        self.gender_field = gender_field
        self.diagnosis_field = diagnosis_field
        self.auto_fix_threshold = auto_fix_threshold

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        if self.gender_field not in df.columns or self.diagnosis_field not in df.columns:
            return ValidationResult(
                rule_name=self.name,
                category=self.category,
                severity=ValidationSeverity.INFO,
                passed=True,
                message="Gender or diagnosis field not present, skipping",
                total_records=len(df),
            )

        # Find male patients with female-only diagnoses
        male_mask = df[self.gender_field] == 'M'

        female_only_mask = df[self.diagnosis_field].fillna('').apply(
            lambda x: any(x.startswith(prefix) for prefix in self.FEMALE_ONLY_DIAGNOSES)
        )

        mismatches = male_mask & female_only_mask
        mismatch_count = mismatches.sum()

        if mismatch_count == 0:
            return ValidationResult(
                rule_name=self.name,
                category=self.category,
                severity=self.severity,
                passed=True,
                message="Gender-diagnosis consistency check passed",
                total_records=len(df),
            )

        auto_fixable = mismatch_count <= self.auto_fix_threshold

        return ValidationResult(
            rule_name=self.name,
            category=self.category,
            severity=self.severity,
            passed=False,
            message=f"Found {mismatch_count} gender-diagnosis mismatches",
            affected_records=int(mismatch_count),
            total_records=len(df),
            affected_percentage=mismatch_count / len(df) * 100 if len(df) > 0 else 0,
            details={"mismatch_indices": df[mismatches].index.tolist()[:20]},
            auto_fixable=auto_fixable,
        )


class VolumeConsistencyRule(ValidationRule):
    """Check volume is within expected range."""

    def __init__(self, expected_count: int, tolerance_pct: float = 0.20):
        super().__init__(
            name="volume_consistency",
            category="consistency",
            severity=ValidationSeverity.WARNING,
            auto_fixable=False
        )
        self.expected_count = expected_count
        self.tolerance_pct = tolerance_pct

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        actual_count = len(df)
        lower_bound = self.expected_count * (1 - self.tolerance_pct)
        upper_bound = self.expected_count * (1 + self.tolerance_pct)

        if lower_bound <= actual_count <= upper_bound:
            return ValidationResult(
                rule_name=self.name,
                category=self.category,
                severity=self.severity,
                passed=True,
                message=f"Volume ({actual_count:,}) within expected range",
                total_records=actual_count,
                details={
                    "expected": self.expected_count,
                    "actual": actual_count,
                    "deviation_pct": (actual_count - self.expected_count) / self.expected_count * 100
                }
            )

        deviation = (actual_count - self.expected_count) / self.expected_count * 100

        return ValidationResult(
            rule_name=self.name,
            category=self.category,
            severity=self.severity,
            passed=False,
            message=f"Volume deviation: {deviation:+.1f}% from expected",
            affected_records=abs(actual_count - self.expected_count),
            total_records=actual_count,
            affected_percentage=abs(deviation),
            details={
                "expected": self.expected_count,
                "actual": actual_count,
                "deviation_pct": deviation
            },
            auto_fixable=False,
        )
