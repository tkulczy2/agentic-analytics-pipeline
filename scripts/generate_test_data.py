#!/usr/bin/env python3
"""
Test data generator for the healthcare analytics pipeline.

Generates realistic simulated healthcare data with configurable quality issues
for testing the validation and analysis agents.
"""
import asyncio
import random
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.services.database import DatabaseService
from src.api.schemas import TestDataConfig


class TestDataGenerator:
    """Generates realistic test healthcare data."""

    # Medical specialties
    SPECIALTIES = [
        "Internal Medicine", "Family Practice", "Cardiology", "Orthopedics",
        "Dermatology", "Neurology", "Oncology", "Psychiatry", "Pediatrics",
        "Emergency Medicine", "General Surgery", "Radiology"
    ]

    # Place of service codes
    PLACE_OF_SERVICE = ["11", "21", "22", "23", "31", "32", "41", "42", "51", "52", "81"]

    # Service categories
    SERVICE_CATEGORIES = [
        "Office Visit", "Inpatient", "Outpatient", "Emergency", "Lab",
        "Imaging", "Surgery", "Therapy", "DME", "Other"
    ]

    # ICD-10 diagnosis codes (sample)
    DIAGNOSES = [
        "E11.9", "I10", "J06.9", "M54.5", "R10.9", "K21.0", "F32.9",
        "J18.9", "N39.0", "G43.909", "E78.5", "J45.909", "Z00.00",
        "Z34.90", "O09.90", "O80"  # Include pregnancy codes
    ]

    # Drug names
    DRUGS = [
        "Lisinopril", "Metformin", "Atorvastatin", "Omeprazole", "Amlodipine",
        "Levothyroxine", "Metoprolol", "Albuterol", "Gabapentin", "Losartan",
        "Hydrochlorothiazide", "Sertraline", "Simvastatin", "Montelukast"
    ]

    # Therapeutic classes
    THERAPEUTIC_CLASSES = [
        "Cardiovascular", "Diabetes", "Respiratory", "Pain Management",
        "Mental Health", "Gastrointestinal", "Endocrine", "Immunology"
    ]

    # Quality measure categories
    QUALITY_CATEGORIES = [
        "preventive_care", "chronic_disease", "care_coordination", "patient_experience"
    ]

    # Quality measure names
    QUALITY_MEASURES = [
        ("QM001", "Diabetes HbA1c Control", "chronic_disease"),
        ("QM002", "Hypertension Control", "chronic_disease"),
        ("QM003", "Breast Cancer Screening", "preventive_care"),
        ("QM004", "Colorectal Cancer Screening", "preventive_care"),
        ("QM005", "Depression Screening", "preventive_care"),
        ("QM006", "Fall Risk Assessment", "care_coordination"),
        ("QM007", "Medication Reconciliation", "care_coordination"),
        ("QM008", "Care Transition Record", "care_coordination"),
        ("QM009", "Patient Satisfaction", "patient_experience"),
        ("QM010", "Access to Care", "patient_experience"),
        ("QM011", "Pneumonia Vaccination", "preventive_care"),
        ("QM012", "Flu Vaccination", "preventive_care"),
        ("QM013", "COPD Management", "chronic_disease"),
        ("QM014", "Heart Failure Management", "chronic_disease"),
        ("QM015", "Tobacco Use Screening", "preventive_care"),
        ("QM016", "BMI Assessment", "preventive_care"),
        ("QM017", "Eye Exam - Diabetic", "chronic_disease"),
        ("QM018", "Kidney Health", "chronic_disease"),
        ("QM019", "Advance Care Planning", "care_coordination"),
        ("QM020", "Hospital Readmission", "care_coordination"),
        ("QM021", "Provider Communication", "patient_experience"),
        ("QM022", "Timely Appointments", "patient_experience"),
        ("QM023", "Overall Rating", "patient_experience"),
    ]

    def __init__(self, database: Optional[DatabaseService] = None):
        """Initialize the generator."""
        self.database = database or DatabaseService()

    async def generate_all(self, config: TestDataConfig) -> Dict[str, int]:
        """
        Generate all test datasets.

        Args:
            config: Configuration for data generation

        Returns:
            Dictionary with record counts per table
        """
        records = {}

        # Generate members first
        members_df = self._generate_members(config.num_members)
        await self._insert_data("members", members_df)
        records["members"] = len(members_df)

        # Generate medical claims
        medical_df = self._generate_medical_claims(
            members_df,
            config.num_medical_claims,
            include_duplicates=config.include_duplicates,
            include_negative_amounts=config.include_negative_amounts,
            include_future_dates=config.include_future_dates,
            include_gender_mismatch=config.include_gender_mismatch,
            include_high_cost_outliers=config.include_high_cost_outliers,
        )
        await self._insert_data("medical_claims", medical_df)
        records["medical_claims"] = len(medical_df)

        # Generate pharmacy claims
        pharmacy_df = self._generate_pharmacy_claims(
            members_df,
            config.num_pharmacy_claims,
            include_duplicates=config.include_duplicates,
            include_negative_amounts=config.include_negative_amounts,
        )
        await self._insert_data("pharmacy_claims", pharmacy_df)
        records["pharmacy_claims"] = len(pharmacy_df)

        # Generate quality measures
        quality_df = self._generate_quality_measures(config.num_quality_measures)
        await self._insert_data("quality_measures", quality_df)
        records["quality_measures"] = len(quality_df)

        return records

    def _generate_members(self, num_members: int) -> pd.DataFrame:
        """Generate member attribution data."""
        # Age distribution weighted toward Medicare (65+)
        age_weights = [0.05] * 10 + [0.02] * 35 + [0.15] * 10 + [0.10] * 10 + [0.05] * 10 + [0.02] * 25
        ages = np.random.choice(range(100), size=num_members, p=np.array(age_weights[:100])/sum(age_weights[:100]))

        today = datetime.now()
        dobs = [today - timedelta(days=int(age * 365.25 + random.randint(0, 364))) for age in ages]

        # Risk scores - log-normal distribution
        risk_scores = np.random.lognormal(mean=0, sigma=0.5, size=num_members)
        risk_scores = np.clip(risk_scores, 0.3, 5.0)  # Clip to reasonable range

        def categorize_risk(score):
            if score < 0.8:
                return "Low"
            elif score > 1.5:
                return "High"
            return "Medium"

        members = []
        for i in range(num_members):
            member_id = f"M{str(i+1).zfill(8)}"

            # Random PCP
            pcp_id = f"PCP{str(random.randint(1, 200)).zfill(4)}"
            pcp_name = f"Dr. {random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis'])} {random.choice(['A', 'B', 'C', 'D', 'E'])}"

            # Attribution dates
            attr_start = today - timedelta(days=random.randint(30, 730))
            attr_end = None if random.random() > 0.1 else today - timedelta(days=random.randint(1, 29))

            members.append({
                "member_id": member_id,
                "first_name": f"First{i}",
                "last_name": f"Last{i}",
                "date_of_birth": dobs[i].date(),
                "gender": random.choice(["M", "F"]),
                "attribution_start_date": attr_start.date(),
                "attribution_end_date": attr_end.date() if attr_end else None,
                "primary_pcp_id": pcp_id,
                "pcp_name": pcp_name,
                "hcc_risk_score": round(risk_scores[i], 4),
                "risk_category": categorize_risk(risk_scores[i]),
            })

        return pd.DataFrame(members)

    def _generate_medical_claims(
        self,
        members_df: pd.DataFrame,
        num_claims: int,
        include_duplicates: bool = True,
        include_negative_amounts: bool = True,
        include_future_dates: bool = True,
        include_gender_mismatch: bool = True,
        include_high_cost_outliers: bool = True,
    ) -> pd.DataFrame:
        """Generate medical claims data with optional quality issues."""
        member_ids = members_df["member_id"].tolist()
        member_genders = dict(zip(members_df["member_id"], members_df["gender"]))

        today = datetime.now()
        year = today.year
        current_month = today.month

        claims = []
        for i in range(num_claims):
            claim_id = f"MC{str(i+1).zfill(10)}"
            member_id = random.choice(member_ids)

            # Service date - random date in the past 12 months up to today
            days_back = random.randint(1, 365)
            service_date = today - timedelta(days=days_back)

            # Paid date - 15-60 days after service
            paid_date = service_date + timedelta(days=random.randint(15, 60))

            # Amount - log-normal distribution
            amount = np.random.lognormal(mean=5, sigma=1.5)
            amount = max(10, min(amount, 50000))  # Base claims $10 - $50K

            # ER and inpatient flags
            is_er = random.random() < 0.08
            is_inpatient = random.random() < 0.03

            if is_inpatient:
                amount *= 5  # Inpatient is more expensive
            elif is_er:
                amount *= 2  # ER is more expensive

            diagnosis = random.choice(self.DIAGNOSES[:-3])  # Exclude pregnancy codes initially

            claims.append({
                "claim_id": claim_id,
                "member_id": member_id,
                "service_date": service_date.date(),
                "paid_date": paid_date.date(),
                "paid_amount": round(amount, 2),
                "allowed_amount": round(amount * random.uniform(1.0, 1.3), 2),
                "place_of_service": random.choice(self.PLACE_OF_SERVICE),
                "provider_specialty": random.choice(self.SPECIALTIES),
                "primary_diagnosis": diagnosis,
                "claim_status": "PAID",
                "service_category": random.choice(self.SERVICE_CATEGORIES),
                "er_visit": is_er,
                "inpatient_admit": is_inpatient,
            })

        df = pd.DataFrame(claims)

        # Add intentional quality issues
        if include_duplicates:
            # Add ~2% duplicates (same data, different claim_id to avoid PK violation)
            num_dupes = int(num_claims * 0.02)
            if num_dupes > 0:
                dupe_indices = random.sample(range(len(df)), num_dupes)
                dupes = df.iloc[dupe_indices].copy()
                # Assign new unique claim IDs to duplicates (same content, different ID)
                for i, idx in enumerate(dupes.index):
                    dupes.at[idx, "claim_id"] = f"MC{str(num_claims + i + 1).zfill(10)}"
                df = pd.concat([df, dupes], ignore_index=True)

        if include_negative_amounts:
            # Add ~0.5% negative amounts
            num_negative = int(num_claims * 0.005)
            negative_indices = random.sample(range(len(df)), num_negative)
            df.loc[negative_indices, "paid_amount"] = df.loc[negative_indices, "paid_amount"] * -1

        if include_future_dates:
            # Add ~0.3% future dates (year typo)
            num_future = int(num_claims * 0.003)
            future_indices = random.sample(range(len(df)), num_future)
            for idx in future_indices:
                current_date = pd.to_datetime(df.loc[idx, "service_date"])
                df.loc[idx, "service_date"] = (current_date + pd.DateOffset(years=1)).date()

        if include_gender_mismatch:
            # Add 5 males with pregnancy codes
            male_members = members_df[members_df["gender"] == "M"]["member_id"].tolist()
            if male_members and len(df) >= 5:
                male_claims = df[df["member_id"].isin(male_members)].head(5).index.tolist()
                pregnancy_codes = ["Z34.90", "O09.90", "O80"]
                for idx in male_claims[:5]:
                    df.loc[idx, "primary_diagnosis"] = random.choice(pregnancy_codes)

        if include_high_cost_outliers:
            # Add 3 high-cost outliers > $500K
            outlier_indices = random.sample(range(len(df)), 3)
            for idx in outlier_indices:
                df.loc[idx, "paid_amount"] = random.uniform(500001, 1000000)

        return df

    def _generate_pharmacy_claims(
        self,
        members_df: pd.DataFrame,
        num_claims: int,
        include_duplicates: bool = True,
        include_negative_amounts: bool = True,
    ) -> pd.DataFrame:
        """Generate pharmacy claims data."""
        member_ids = members_df["member_id"].tolist()
        today = datetime.now()

        claims = []
        for i in range(num_claims):
            claim_id = f"RX{str(i+1).zfill(10)}"
            member_id = random.choice(member_ids)

            # Fill date - random date in the past 12 months up to today
            days_back = random.randint(1, 365)
            fill_date = today - timedelta(days=days_back)

            # Amount - log-normal distribution, typical Rx costs
            amount = np.random.lognormal(mean=3, sigma=1)
            amount = max(5, min(amount, 5000))

            claims.append({
                "claim_id": claim_id,
                "member_id": member_id,
                "fill_date": fill_date.date(),
                "paid_amount": round(amount, 2),
                "drug_name": random.choice(self.DRUGS),
                "generic_indicator": random.random() < 0.7,
                "days_supply": random.choice([30, 60, 90]),
                "therapeutic_class": random.choice(self.THERAPEUTIC_CLASSES),
                "condition_category": random.choice(["Chronic", "Acute", "Maintenance"]),
            })

        df = pd.DataFrame(claims)

        # Add intentional quality issues
        if include_duplicates:
            num_dupes = int(num_claims * 0.02)
            if num_dupes > 0:
                dupe_indices = random.sample(range(len(df)), num_dupes)
                dupes = df.iloc[dupe_indices].copy()
                # Assign new unique claim IDs to duplicates
                for i, idx in enumerate(dupes.index):
                    dupes.at[idx, "claim_id"] = f"RX{str(num_claims + i + 1).zfill(10)}"
                df = pd.concat([df, dupes], ignore_index=True)

        if include_negative_amounts:
            num_negative = int(num_claims * 0.005)
            negative_indices = random.sample(range(len(df)), num_negative)
            df.loc[negative_indices, "paid_amount"] = df.loc[negative_indices, "paid_amount"] * -1

        return df

    def _generate_quality_measures(self, num_measures: int) -> pd.DataFrame:
        """Generate quality measures data."""
        today = datetime.now()
        year = today.year
        month = today.month

        measures = []
        for i, (measure_id, measure_name, category) in enumerate(self.QUALITY_MEASURES[:num_measures]):
            # Generate realistic performance rates
            # Most measures should be in 70-95% range
            base_rate = random.uniform(65, 95)

            # Add some variation by category
            if category == "chronic_disease":
                base_rate = random.uniform(60, 90)  # Harder to achieve
            elif category == "preventive_care":
                base_rate = random.uniform(70, 95)
            elif category == "care_coordination":
                base_rate = random.uniform(65, 92)
            else:  # patient_experience
                base_rate = random.uniform(75, 95)

            # Calculate numerator/denominator to match rate
            denominator = random.randint(800, 1200)
            numerator = int(denominator * base_rate / 100)
            exclusions = random.randint(10, 100)

            actual_rate = (numerator / denominator) * 100 if denominator > 0 else 0

            # National benchmark (slightly better than average)
            benchmark = random.uniform(actual_rate - 10, actual_rate + 15)
            benchmark = max(50, min(benchmark, 98))

            # Measure weight
            weight = 2.0 if category == "chronic_disease" else 1.5 if category == "care_coordination" else 1.0

            measures.append({
                "measure_id": measure_id,
                "measure_name": measure_name,
                "measure_category": category,
                "numerator": numerator,
                "denominator": denominator,
                "exclusions": exclusions,
                "performance_rate": round(actual_rate, 2),
                "national_benchmark": round(benchmark, 2),
                "measure_weight": weight,
                "performance_year": year,
                "performance_month": month,
            })

        return pd.DataFrame(measures)

    async def _insert_data(self, table_name: str, df: pd.DataFrame):
        """Insert data into the database."""
        # Truncate existing data
        await self.database.truncate_table(table_name)

        # Insert new data
        await self.database.insert_dataframe(df, table_name)


async def main():
    """Main entry point for standalone execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate test healthcare data")
    parser.add_argument("--members", type=int, default=12000, help="Number of members")
    parser.add_argument("--medical-claims", type=int, default=50000, help="Number of medical claims")
    parser.add_argument("--pharmacy-claims", type=int, default=15000, help="Number of pharmacy claims")
    parser.add_argument("--quality-measures", type=int, default=23, help="Number of quality measures")
    parser.add_argument("--no-issues", action="store_true", help="Generate clean data without quality issues")

    args = parser.parse_args()

    config = TestDataConfig(
        num_members=args.members,
        num_medical_claims=args.medical_claims,
        num_pharmacy_claims=args.pharmacy_claims,
        num_quality_measures=args.quality_measures,
        include_duplicates=not args.no_issues,
        include_negative_amounts=not args.no_issues,
        include_future_dates=not args.no_issues,
        include_gender_mismatch=not args.no_issues,
        include_high_cost_outliers=not args.no_issues,
    )

    generator = TestDataGenerator()
    records = await generator.generate_all(config)

    print("\nTest data generated successfully!")
    print("-" * 40)
    for table, count in records.items():
        print(f"  {table}: {count:,} records")


if __name__ == "__main__":
    asyncio.run(main())
