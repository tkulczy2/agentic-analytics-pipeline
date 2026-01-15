#!/usr/bin/env python3
"""
Demo script for the Agentic Analytics Pipeline.

This script demonstrates the complete pipeline execution:
1. Generate test data with intentional quality issues
2. Start a workflow
3. Monitor execution progress
4. Display results summary
"""
import asyncio
import json
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, "/app")

from src.agents.orchestrator import OrchestratorAgent
from src.services.state_manager import StateManager
from src.services.database import DatabaseService
from src.services.email_service import EmailService
from src.api.schemas import TestDataConfig
from scripts.generate_test_data import TestDataGenerator
from src.models.workflow import WorkflowStatus


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_section(text: str):
    """Print a section header."""
    print(f"\n>>> {text}")
    print("-" * 40)


def print_metric(label: str, value, indent: int = 2):
    """Print a formatted metric."""
    spaces = " " * indent
    if isinstance(value, float):
        if abs(value) >= 1000000:
            print(f"{spaces}{label}: ${value:,.0f}")
        elif abs(value) >= 1:
            print(f"{spaces}{label}: {value:.2f}")
        else:
            print(f"{spaces}{label}: {value:.4f}")
    elif isinstance(value, int):
        print(f"{spaces}{label}: {value:,}")
    else:
        print(f"{spaces}{label}: {value}")


async def generate_test_data():
    """Generate test data with intentional quality issues."""
    print_section("Generating Test Data")

    config = TestDataConfig(
        num_members=12000,
        num_medical_claims=50000,
        num_pharmacy_claims=15000,
        num_quality_measures=23,
        include_duplicates=True,
        include_negative_amounts=True,
        include_future_dates=True,
        include_gender_mismatch=True,
        include_high_cost_outliers=True,
    )

    print(f"  Members: {config.num_members:,}")
    print(f"  Medical Claims: {config.num_medical_claims:,}")
    print(f"  Pharmacy Claims: {config.num_pharmacy_claims:,}")
    print(f"  Quality Measures: {config.num_quality_measures}")
    print(f"\n  Including intentional quality issues:")
    print(f"    - ~2% duplicate claims")
    print(f"    - ~0.5% negative amounts")
    print(f"    - ~0.3% future date typos")
    print(f"    - 5 gender-diagnosis mismatches")
    print(f"    - 3 high-cost outliers (>$500K)")

    generator = TestDataGenerator()
    records = await generator.generate_all(config)

    print(f"\n  Test data generated successfully!")
    for table, count in records.items():
        print(f"    {table}: {count:,} records")

    return records


async def run_workflow():
    """Start and monitor a workflow."""
    print_section("Starting Analytics Workflow")

    # Initialize services
    state_manager = StateManager()
    database = DatabaseService()
    email_service = EmailService()

    # Create orchestrator
    orchestrator = OrchestratorAgent(
        state_manager=state_manager,
        database=database,
        email_service=email_service
    )

    # Start workflow
    contract_id = "VBC-MSSP-001"
    performance_year = datetime.now().year
    performance_month = 11

    print(f"  Contract: {contract_id}")
    print(f"  Period: {performance_year} M{performance_month:02d}")

    state = await orchestrator.start_workflow(
        contract_id=contract_id,
        performance_year=performance_year,
        performance_month=performance_month
    )

    print(f"  Workflow ID: {state.workflow_id}")
    print(f"  Status: {state.status.value}")

    # Monitor progress
    print_section("Monitoring Workflow Execution")

    agent_names = {
        "data": "Data Extraction",
        "validation": "Validation",
        "analysis": "Analysis",
        "reporting": "Reporting"
    }

    max_wait = 300  # 5 minutes timeout
    start_time = time.time()

    while True:
        await asyncio.sleep(2)

        state = await state_manager.get_workflow(state.workflow_id)
        if not state:
            print("  ERROR: Workflow not found!")
            break

        # Print agent statuses
        print(f"\r  Progress: ", end="")
        for key, name in agent_names.items():
            status = getattr(state, f"{key}_agent_status")
            symbol = "✓" if status.value == "completed" else "✗" if status.value == "failed" else "○" if status.value == "pending" else "◉"
            print(f"{symbol} {name}  ", end="")

        if state.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED):
            print()  # New line
            break

        if time.time() - start_time > max_wait:
            print("\n  TIMEOUT: Workflow took too long")
            break

    return state


def print_results(state):
    """Print workflow results summary."""
    print_header("WORKFLOW RESULTS")

    print_section("Workflow Summary")
    print_metric("Workflow ID", state.workflow_id)
    print_metric("Status", state.status.value.upper())
    print_metric("Contract", state.contract_id)
    print_metric("Period", f"{state.performance_year} M{state.performance_month:02d}")

    if state.completed_at and state.started_at:
        duration = (state.completed_at - state.started_at).total_seconds()
        print_metric("Duration", f"{duration:.1f} seconds")

    # Data extraction results
    print_section("Data Extraction")
    for dataset, count in state.records_extracted.items():
        print_metric(dataset.replace("_", " ").title(), count)

    # Validation results
    print_section("Validation")
    print_metric("Passed", "Yes" if state.validation_passed else "No")
    print_metric("Auto-fixes Applied", state.auto_fixes_applied)
    print_metric("Warnings", len(state.warnings))
    print_metric("Critical Errors", len(state.critical_errors))

    if state.warnings:
        print("\n  Warnings:")
        for w in state.warnings[:5]:
            print(f"    - {w.get('message', w)}")

    # Financial metrics
    if state.financial_metrics:
        print_section("Financial Performance")
        fm = state.financial_metrics
        print_metric("Baseline Spending", fm.get("baseline_spending", 0))
        print_metric("Actual Spending", fm.get("actual_spending", 0))
        print_metric("Total Savings", fm.get("total_savings", 0))
        print_metric("Savings %", f"{fm.get('savings_percentage', 0):.1f}%")
        print_metric("Shared Savings", fm.get("shared_savings_amount", 0))
        print_metric("Members", fm.get("average_members", 0))
        print_metric("ER Visits/1000", fm.get("er_visits_per_1000", 0))
        print_metric("Admits/1000", fm.get("admits_per_1000", 0))

    # Quality metrics
    if state.quality_metrics:
        print_section("Quality Performance")
        qm = state.quality_metrics
        print_metric("Composite Score", f"{qm.get('composite_score', 0):.1f}%")
        print_metric("Quality Gate", qm.get("quality_gate_status", "pending").upper())
        print_metric("Preventive Care", f"{qm.get('preventive_care_score', 0):.1f}%")
        print_metric("Chronic Disease", f"{qm.get('chronic_disease_score', 0):.1f}%")
        print_metric("Care Coordination", f"{qm.get('care_coordination_score', 0):.1f}%")
        print_metric("Patient Experience", f"{qm.get('patient_experience_score', 0):.1f}%")

    # Risk stratification
    if state.risk_metrics:
        print_section("Risk Stratification")
        rm = state.risk_metrics
        print_metric("Total Members", rm.get("total_members", 0))
        print_metric("Low Risk", f"{rm.get('low_risk_count', 0):,} ({rm.get('low_risk_pct', 0):.1f}%)")
        print_metric("Medium Risk", f"{rm.get('medium_risk_count', 0):,} ({rm.get('medium_risk_pct', 0):.1f}%)")
        print_metric("High Risk", f"{rm.get('high_risk_count', 0):,} ({rm.get('high_risk_pct', 0):.1f}%)")
        print_metric("Avg Risk Score", rm.get("average_risk_score", 0))

    # Predictions
    if state.predictions:
        print_section("Year-End Predictions")
        pred = state.predictions
        print_metric("Projected Savings", pred.get("projected_year_end_savings", 0))
        print_metric("Projected Shared Savings", pred.get("projected_shared_savings", 0))
        print_metric("Probability of Target", f"{pred.get('probability_meeting_target', 0)*100:.0f}%")

        if pred.get("risks"):
            print("\n  Identified Risks:")
            for risk in pred["risks"][:3]:
                print(f"    - [{risk.get('severity', 'medium').upper()}] {risk.get('title', 'Risk')}")

        if pred.get("opportunities"):
            print("\n  Opportunities:")
            for opp in pred["opportunities"][:3]:
                print(f"    - {opp.get('title', 'Opportunity')}")

    # Reports
    if state.reports_generated:
        print_section("Generated Reports")
        for report in state.reports_generated:
            print(f"    {report}")

    # Errors
    if state.errors:
        print_section("Errors")
        for error in state.errors:
            print(f"    - {error.get('message', error)}")


async def main():
    """Main demo execution."""
    print_header("AGENTIC ANALYTICS PIPELINE DEMO")
    print(f"\n  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("  This demo will:")
    print("    1. Generate test healthcare data with quality issues")
    print("    2. Run the complete analytics pipeline")
    print("    3. Display results and generated reports")

    try:
        # Step 1: Generate test data
        await generate_test_data()

        # Step 2: Run workflow
        state = await run_workflow()

        # Step 3: Print results
        if state:
            print_results(state)

        print_header("DEMO COMPLETE")

        if state and state.status == WorkflowStatus.COMPLETED:
            print("\n  The pipeline completed successfully!")
            print("  Check the following for more details:")
            print("    - MailHog UI: http://localhost:8025 (email notifications)")
            print("    - pgAdmin: http://localhost:8080 (database)")
            print("    - Redis Commander: http://localhost:8081 (state)")
            print(f"    - Reports: /app/reports/")
        else:
            print("\n  The pipeline did not complete successfully.")
            print("  Check the errors section above for details.")

    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
