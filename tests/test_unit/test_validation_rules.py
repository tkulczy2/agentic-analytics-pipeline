"""Unit tests for validation rules."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.validation.rules import (
    ValidationSeverity,
    RequiredFieldsRule,
    NullValueRule,
    AgeRangeRule,
    CostAmountRule,
    DateLogicRule,
    DuplicateRule,
    GenderDiagnosisRule,
    VolumeConsistencyRule,
)
from src.validation.remediation import AutoRemediation


class TestRequiredFieldsRule:
    """Tests for RequiredFieldsRule."""

    def test_all_fields_present(self):
        """Test when all required fields are present."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["a", "b", "c"],
            "value": [10, 20, 30]
        })
        rule = RequiredFieldsRule(["id", "name", "value"])

        result = rule.validate(df)

        assert result.passed
        assert result.severity == ValidationSeverity.CRITICAL

    def test_missing_fields(self):
        """Test when required fields are missing."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["a", "b", "c"]
        })
        rule = RequiredFieldsRule(["id", "name", "value", "other"])

        result = rule.validate(df)

        assert not result.passed
        assert "value" in result.details["missing_fields"]
        assert "other" in result.details["missing_fields"]


class TestNullValueRule:
    """Tests for NullValueRule."""

    def test_no_nulls(self):
        """Test when there are no null values."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["a", "b", "c"]
        })
        rule = NullValueRule(["id", "name"])

        result = rule.validate(df)

        assert result.passed

    def test_some_nulls_warning(self):
        """Test when null percentage is below threshold (warning)."""
        df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5, None],  # 1/6 = 16.7% - but only 1 null
            "name": ["a", "b", "c", "d", "e", "f"]
        })
        # With 100 records and 4 nulls = 4% < 5% threshold
        df = pd.DataFrame({
            "id": list(range(96)) + [None] * 4,
            "name": ["a"] * 100
        })
        rule = NullValueRule(["id", "name"], critical_threshold=0.05)

        result = rule.validate(df)

        assert not result.passed  # Has nulls
        assert result.severity == ValidationSeverity.WARNING  # Below threshold

    def test_many_nulls_critical(self):
        """Test when null percentage exceeds threshold (critical)."""
        df = pd.DataFrame({
            "id": list(range(90)) + [None] * 10,  # 10% nulls
            "name": ["a"] * 100
        })
        rule = NullValueRule(["id", "name"], critical_threshold=0.05)

        result = rule.validate(df)

        assert not result.passed
        assert result.severity == ValidationSeverity.CRITICAL


class TestAgeRangeRule:
    """Tests for AgeRangeRule."""

    def test_valid_ages(self):
        """Test when all ages are valid."""
        today = datetime.now()
        df = pd.DataFrame({
            "date_of_birth": [
                (today - timedelta(days=365*30)).date(),
                (today - timedelta(days=365*50)).date(),
                (today - timedelta(days=365*70)).date(),
            ]
        })
        rule = AgeRangeRule("date_of_birth")

        result = rule.validate(df)

        assert result.passed

    def test_invalid_ages(self):
        """Test when ages are outside valid range."""
        today = datetime.now()
        df = pd.DataFrame({
            "date_of_birth": [
                (today - timedelta(days=365*30)).date(),
                (today + timedelta(days=365*5)).date(),  # Future = negative age
                (today - timedelta(days=365*130)).date(),  # 130 years old
            ]
        })
        rule = AgeRangeRule("date_of_birth")

        result = rule.validate(df)

        assert not result.passed
        assert result.affected_records == 2


class TestCostAmountRule:
    """Tests for CostAmountRule."""

    def test_valid_amounts(self):
        """Test when all amounts are valid."""
        df = pd.DataFrame({
            "paid_amount": [100, 500, 1000, 5000]
        })
        rule = CostAmountRule(["paid_amount"])

        result = rule.validate(df)

        assert result.passed

    def test_high_cost_outliers(self):
        """Test detection of high-cost outliers."""
        df = pd.DataFrame({
            "paid_amount": [100, 500, 600000, 750000]  # 2 > $500K
        })
        rule = CostAmountRule(["paid_amount"], high_cost_threshold=500000)

        result = rule.validate(df)

        assert not result.passed
        assert "paid_amount_high_cost" in result.details

    def test_negative_amounts(self):
        """Test detection of negative amounts."""
        df = pd.DataFrame({
            "paid_amount": [100, -50, 200, -30]  # 2 negatives
        })
        rule = CostAmountRule(["paid_amount"])

        result = rule.validate(df)

        assert not result.passed
        assert "paid_amount_negative" in result.details


class TestDuplicateRule:
    """Tests for DuplicateRule."""

    def test_no_duplicates(self):
        """Test when there are no duplicates."""
        df = pd.DataFrame({
            "claim_id": ["C001", "C002", "C003"],
            "amount": [100, 200, 300]
        })
        rule = DuplicateRule(["claim_id"])

        result = rule.validate(df)

        assert result.passed

    def test_with_duplicates_fixable(self):
        """Test when duplicates are below threshold (auto-fixable)."""
        df = pd.DataFrame({
            "claim_id": ["C001", "C001", "C002", "C003"] + [f"C{i:03d}" for i in range(4, 100)],
            "amount": [100] * 99
        })
        rule = DuplicateRule(["claim_id"], critical_threshold=0.05)

        result = rule.validate(df)

        assert not result.passed
        assert result.auto_fixable  # Below 5% threshold

    def test_with_duplicates_critical(self):
        """Test when duplicates exceed threshold (critical)."""
        # 10 duplicates out of 20 = 50%
        df = pd.DataFrame({
            "claim_id": ["C001"] * 10 + ["C002"] * 10,
            "amount": [100] * 20
        })
        rule = DuplicateRule(["claim_id"], critical_threshold=0.05)

        result = rule.validate(df)

        assert not result.passed
        assert result.severity == ValidationSeverity.CRITICAL
        assert not result.auto_fixable


class TestGenderDiagnosisRule:
    """Tests for GenderDiagnosisRule."""

    def test_no_mismatches(self):
        """Test when there are no gender-diagnosis mismatches."""
        df = pd.DataFrame({
            "gender": ["M", "F", "M", "F"],
            "primary_diagnosis": ["E11.9", "Z34.90", "I10", "O09.90"]  # Pregnancy codes for females
        })
        rule = GenderDiagnosisRule()

        result = rule.validate(df)

        assert result.passed

    def test_with_mismatches_fixable(self):
        """Test when there are fixable mismatches (< 10)."""
        df = pd.DataFrame({
            "gender": ["M", "M", "F", "F"],  # Males with pregnancy codes
            "primary_diagnosis": ["Z34.90", "O09.90", "E11.9", "I10"]
        })
        rule = GenderDiagnosisRule(auto_fix_threshold=10)

        result = rule.validate(df)

        assert not result.passed
        assert result.auto_fixable  # Only 2 mismatches

    def test_with_mismatches_not_fixable(self):
        """Test when too many mismatches to auto-fix."""
        df = pd.DataFrame({
            "gender": ["M"] * 15,
            "primary_diagnosis": ["Z34.90"] * 15  # All males with pregnancy
        })
        rule = GenderDiagnosisRule(auto_fix_threshold=10)

        result = rule.validate(df)

        assert not result.passed
        assert not result.auto_fixable  # 15 > 10 threshold


class TestAutoRemediation:
    """Tests for auto-remediation strategies."""

    def test_fix_duplicates(self):
        """Test duplicate removal."""
        df = pd.DataFrame({
            "claim_id": ["C001", "C001", "C002", "C003"],
            "amount": [100, 100, 200, 300]
        })

        fixed_df, results = AutoRemediation.fix_duplicates(df, ["claim_id"])

        assert len(fixed_df) == 3  # Duplicate removed
        assert results[0].success
        assert results[0].records_fixed == 1

    def test_fix_negative_amounts(self):
        """Test negative amount conversion."""
        df = pd.DataFrame({
            "paid_amount": [100, -50, 200, -30],
        })

        fixed_df, results = AutoRemediation.fix_negative_amounts(df, ["paid_amount"])

        assert (fixed_df["paid_amount"] >= 0).all()  # All positive now
        assert results[0].success
        assert results[0].records_fixed == 2

    def test_fix_gender_mismatch(self):
        """Test gender correction for pregnancy codes."""
        df = pd.DataFrame({
            "gender": ["M", "M", "F"],
            "primary_diagnosis": ["Z34.90", "E11.9", "O09.90"]
        })

        fixed_df, results = AutoRemediation.fix_gender_mismatch(df)

        assert fixed_df.loc[0, "gender"] == "F"  # First male corrected
        assert fixed_df.loc[1, "gender"] == "M"  # Second male unchanged (no pregnancy code)
        assert results[0].records_fixed == 1
