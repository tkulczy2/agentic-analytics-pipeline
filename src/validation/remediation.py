"""Auto-remediation strategies for common data quality issues."""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RemediationResult:
    """Result of an auto-remediation attempt."""
    strategy_name: str
    success: bool
    records_fixed: int
    message: str
    details: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "success": self.success,
            "records_fixed": self.records_fixed,
            "message": self.message,
            "details": self.details or {}
        }


class AutoRemediation:
    """Auto-remediation strategies for data quality issues."""

    @staticmethod
    def fix_date_formats(
        df: pd.DataFrame,
        date_fields: List[str],
        success_threshold: float = 0.95
    ) -> Tuple[pd.DataFrame, List[RemediationResult]]:
        """
        Try multiple date formats and convert if >95% success rate.

        Args:
            df: DataFrame to fix
            date_fields: List of date field names
            success_threshold: Minimum success rate to apply fix

        Returns:
            Tuple of (fixed DataFrame, list of remediation results)
        """
        results = []
        df = df.copy()

        date_formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
            "%m-%d-%Y",
            "%d-%m-%Y",
        ]

        for field in date_fields:
            if field not in df.columns:
                continue

            # Skip if already datetime
            if pd.api.types.is_datetime64_any_dtype(df[field]):
                continue

            original_valid = pd.to_datetime(df[field], errors='coerce').notna().sum()
            best_format = None
            best_count = original_valid

            for fmt in date_formats:
                try:
                    parsed = pd.to_datetime(df[field], format=fmt, errors='coerce')
                    valid_count = parsed.notna().sum()
                    if valid_count > best_count:
                        best_count = valid_count
                        best_format = fmt
                except Exception:
                    continue

            if best_format and best_count / len(df) >= success_threshold:
                df[field] = pd.to_datetime(df[field], format=best_format, errors='coerce')
                records_fixed = best_count - original_valid

                results.append(RemediationResult(
                    strategy_name="fix_date_formats",
                    success=True,
                    records_fixed=int(records_fixed),
                    message=f"Standardized {field} dates using format {best_format}",
                    details={"field": field, "format": best_format, "success_rate": best_count / len(df)}
                ))
                logger.info(f"Fixed date format for {field}: {records_fixed} records")

        return df, results

    @staticmethod
    def fix_duplicates(
        df: pd.DataFrame,
        key_fields: List[str],
        critical_threshold: float = 0.05
    ) -> Tuple[pd.DataFrame, List[RemediationResult]]:
        """
        Remove duplicates if less than critical threshold.

        Args:
            df: DataFrame to fix
            key_fields: Fields to use for duplicate detection
            critical_threshold: Maximum duplicate percentage to auto-fix

        Returns:
            Tuple of (fixed DataFrame, list of remediation results)
        """
        results = []
        df = df.copy()

        available_keys = [f for f in key_fields if f in df.columns]
        if not available_keys:
            return df, results

        duplicates = df.duplicated(subset=available_keys, keep='first')
        dup_count = duplicates.sum()
        dup_pct = dup_count / len(df) if len(df) > 0 else 0

        if dup_count == 0:
            return df, results

        if dup_pct <= critical_threshold:
            df = df.drop_duplicates(subset=available_keys, keep='first')
            results.append(RemediationResult(
                strategy_name="fix_duplicates",
                success=True,
                records_fixed=int(dup_count),
                message=f"Removed {dup_count} duplicate records ({dup_pct*100:.2f}%)",
                details={"key_fields": available_keys, "removed_count": int(dup_count)}
            ))
            logger.info(f"Removed {dup_count} duplicates")
        else:
            results.append(RemediationResult(
                strategy_name="fix_duplicates",
                success=False,
                records_fixed=0,
                message=f"Duplicate rate ({dup_pct*100:.2f}%) exceeds threshold ({critical_threshold*100}%)",
                details={"duplicate_pct": dup_pct * 100, "threshold": critical_threshold * 100}
            ))

        return df, results

    @staticmethod
    def fix_negative_amounts(
        df: pd.DataFrame,
        amount_fields: List[str],
        critical_threshold: float = 0.01
    ) -> Tuple[pd.DataFrame, List[RemediationResult]]:
        """
        Convert negative amounts to absolute values if under threshold.

        Args:
            df: DataFrame to fix
            amount_fields: List of amount field names
            critical_threshold: Maximum negative percentage to auto-fix

        Returns:
            Tuple of (fixed DataFrame, list of remediation results)
        """
        results = []
        df = df.copy()

        for field in amount_fields:
            if field not in df.columns:
                continue

            negative_mask = df[field] < 0
            negative_count = negative_mask.sum()
            negative_pct = negative_count / len(df) if len(df) > 0 else 0

            if negative_count == 0:
                continue

            if negative_pct <= critical_threshold:
                df.loc[negative_mask, field] = df.loc[negative_mask, field].abs()
                results.append(RemediationResult(
                    strategy_name="fix_negative_amounts",
                    success=True,
                    records_fixed=int(negative_count),
                    message=f"Converted {negative_count} negative {field} values to absolute",
                    details={"field": field, "fixed_count": int(negative_count)}
                ))
                logger.info(f"Fixed {negative_count} negative values in {field}")
            else:
                results.append(RemediationResult(
                    strategy_name="fix_negative_amounts",
                    success=False,
                    records_fixed=0,
                    message=f"Negative rate ({negative_pct*100:.2f}%) in {field} exceeds threshold",
                    details={"field": field, "negative_pct": negative_pct * 100}
                ))

        return df, results

    @staticmethod
    def fix_future_dates(
        df: pd.DataFrame,
        date_fields: List[str],
        year_typo_threshold: float = 0.80
    ) -> Tuple[pd.DataFrame, List[RemediationResult]]:
        """
        Fix future dates by subtracting 1 year if it's a typo pattern.

        Args:
            df: DataFrame to fix
            date_fields: List of date field names
            year_typo_threshold: Minimum percentage of future dates that are exactly 1 year ahead

        Returns:
            Tuple of (fixed DataFrame, list of remediation results)
        """
        results = []
        df = df.copy()
        today = pd.Timestamp.now().normalize()

        for field in date_fields:
            if field not in df.columns:
                continue

            dates = pd.to_datetime(df[field], errors='coerce')
            future_mask = dates > today

            if future_mask.sum() == 0:
                continue

            # Check for year typo pattern
            one_year_ahead = (dates.dt.year == today.year + 1) & future_mask
            one_year_count = one_year_ahead.sum()
            future_count = future_mask.sum()

            if one_year_count / future_count >= year_typo_threshold:
                # Fix by subtracting 1 year
                fixed_dates = dates.copy()
                fixed_dates[one_year_ahead] = dates[one_year_ahead] - pd.DateOffset(years=1)
                df[field] = fixed_dates

                results.append(RemediationResult(
                    strategy_name="fix_future_dates",
                    success=True,
                    records_fixed=int(one_year_count),
                    message=f"Fixed {one_year_count} future dates in {field} (year typo pattern)",
                    details={"field": field, "pattern": "year_typo", "fixed_count": int(one_year_count)}
                ))
                logger.info(f"Fixed {one_year_count} future dates in {field}")
            else:
                results.append(RemediationResult(
                    strategy_name="fix_future_dates",
                    success=False,
                    records_fixed=0,
                    message=f"Future dates in {field} don't match typo pattern",
                    details={"field": field, "future_count": int(future_count)}
                ))

        return df, results

    @staticmethod
    def fix_gender_mismatch(
        df: pd.DataFrame,
        gender_field: str = "gender",
        diagnosis_field: str = "primary_diagnosis",
        max_fixes: int = 10
    ) -> Tuple[pd.DataFrame, List[RemediationResult]]:
        """
        Fix gender for pregnancy codes if small number of mismatches.

        Args:
            df: DataFrame to fix
            gender_field: Name of gender field
            diagnosis_field: Name of diagnosis field
            max_fixes: Maximum number of records to auto-fix

        Returns:
            Tuple of (fixed DataFrame, list of remediation results)
        """
        results = []
        df = df.copy()

        if gender_field not in df.columns or diagnosis_field not in df.columns:
            return df, results

        female_only_prefixes = ["Z34", "O"]

        male_mask = df[gender_field] == 'M'
        female_only_mask = df[diagnosis_field].fillna('').apply(
            lambda x: any(x.startswith(prefix) for prefix in female_only_prefixes)
        )

        mismatches = male_mask & female_only_mask
        mismatch_count = mismatches.sum()

        if mismatch_count == 0:
            return df, results

        if mismatch_count <= max_fixes:
            df.loc[mismatches, gender_field] = 'F'
            results.append(RemediationResult(
                strategy_name="fix_gender_mismatch",
                success=True,
                records_fixed=int(mismatch_count),
                message=f"Fixed gender to 'F' for {mismatch_count} pregnancy diagnosis records",
                details={"fixed_indices": df[mismatches].index.tolist()}
            ))
            logger.info(f"Fixed {mismatch_count} gender mismatches")
        else:
            results.append(RemediationResult(
                strategy_name="fix_gender_mismatch",
                success=False,
                records_fixed=0,
                message=f"Too many mismatches ({mismatch_count}) to auto-fix (max: {max_fixes})",
                details={"mismatch_count": int(mismatch_count), "max_fixes": max_fixes}
            ))

        return df, results

    @classmethod
    def apply_all_remediations(
        cls,
        df: pd.DataFrame,
        config: Dict[str, Any] = None
    ) -> Tuple[pd.DataFrame, List[RemediationResult]]:
        """
        Apply all applicable remediation strategies.

        Args:
            df: DataFrame to fix
            config: Configuration for remediation thresholds

        Returns:
            Tuple of (fixed DataFrame, list of all remediation results)
        """
        config = config or {}
        all_results = []

        # Date format fixes
        date_fields = config.get("date_fields", ["service_date", "paid_date", "fill_date", "date_of_birth"])
        df, results = cls.fix_date_formats(df, date_fields)
        all_results.extend(results)

        # Duplicate fixes
        key_fields = config.get("key_fields", ["claim_id"])
        df, results = cls.fix_duplicates(df, key_fields)
        all_results.extend(results)

        # Negative amount fixes
        amount_fields = config.get("amount_fields", ["paid_amount", "allowed_amount"])
        df, results = cls.fix_negative_amounts(df, amount_fields)
        all_results.extend(results)

        # Future date fixes
        df, results = cls.fix_future_dates(df, date_fields)
        all_results.extend(results)

        # Gender mismatch fixes
        df, results = cls.fix_gender_mismatch(df)
        all_results.extend(results)

        return df, all_results
