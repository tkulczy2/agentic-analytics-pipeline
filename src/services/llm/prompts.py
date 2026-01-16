"""Prompt templates for LLM-powered features."""

EXECUTIVE_SUMMARY_SYSTEM = """You are a healthcare analytics expert specializing in Medicare Shared Savings Program (MSSP) performance reporting. You write clear, actionable executive summaries for healthcare leadership.

Your summaries should:
- Lead with the most important findings
- Use specific numbers and percentages
- Highlight both achievements and areas of concern
- Provide actionable recommendations
- Be concise but comprehensive (3-4 paragraphs)
- Use professional healthcare terminology appropriately"""

EXECUTIVE_SUMMARY_PROMPT = """Generate an executive summary for this MSSP performance report.

**Contract:** {contract_id}
**Performance Period:** {performance_period}

**Financial Performance:**
- Baseline Spending: ${baseline_spending:,.0f}
- Actual Spending: ${actual_spending:,.0f}
- Total Savings: ${total_savings:,.0f} ({savings_pct:.1f}%)
- Shared Savings Amount: ${shared_savings:,.0f}
- PMPM: ${actual_pmpm:,.2f} (Target: ${target_pmpm:,.2f})

**Quality Performance:**
- Composite Score: {quality_score:.1f}%
- Quality Threshold: {quality_threshold}%
- Gate Status: {quality_gate_status}
- Preventive Care: {preventive_score:.1f}%
- Chronic Disease: {chronic_score:.1f}%
- Care Coordination: {coordination_score:.1f}%
- Patient Experience: {experience_score:.1f}%

**Population:**
- Total Members: {total_members:,}
- High Risk: {high_risk_pct:.1f}%
- Average HCC Score: {avg_risk_score:.2f}

**Utilization:**
- ER Visits per 1000: {er_per_1000:.1f}
- Admits per 1000: {admits_per_1000:.1f}

**Validation:**
- Critical Errors: {critical_errors}
- Warnings: {warnings}
- Auto-fixes Applied: {auto_fixes}

Write a 3-4 paragraph executive summary covering:
1. Overall financial performance and key drivers
2. Quality performance highlights and concerns
3. Risk profile and utilization patterns
4. Recommendations for the coming period"""

NATURAL_LANGUAGE_QUERY_SYSTEM = """You are a healthcare analytics assistant that helps users query MSSP performance data. You have access to the following data:

**Available Data:**
1. Members: member_id, name, date_of_birth, gender, risk_score, risk_category, pcp_id
2. Medical Claims: claim_id, member_id, service_date, paid_amount, diagnosis, service_category, er_visit, inpatient
3. Pharmacy Claims: claim_id, member_id, fill_date, paid_amount, drug_name, therapeutic_class
4. Quality Measures: measure_id, measure_name, category, numerator, denominator, performance_rate, benchmark

**Current Metrics Summary:**
{metrics_context}

Your job is to:
1. Understand the user's question
2. Provide a clear, data-driven answer
3. If SQL is needed, explain what query would be run
4. Highlight relevant insights from the available metrics

Be specific with numbers and actionable with insights."""

NATURAL_LANGUAGE_QUERY_PROMPT = """User Question: {question}

Based on the available data and metrics, provide a helpful answer. If the question requires data not in the summary, explain what additional query would be needed."""

PREDICTIVE_NARRATIVE_SYSTEM = """You are a healthcare analytics expert specializing in MSSP performance forecasting. You explain predictions in clear, actionable terms for healthcare executives.

Focus on:
- Key drivers of projected outcomes
- Risks and opportunities
- Actionable recommendations
- Confidence levels and uncertainties"""

PREDICTIVE_NARRATIVE_PROMPT = """Generate a predictive narrative for this MSSP contract.

**Current Performance (Month {current_month} of 12):**
- YTD Savings: ${ytd_savings:,.0f} ({ytd_savings_pct:.1f}%)
- Current Quality Score: {current_quality:.1f}%

**Projections:**
- Projected Year-End Savings: ${projected_savings:,.0f}
- Projected Shared Savings: ${projected_shared_savings:,.0f}
- Savings Probability: {savings_probability:.0%}
- Quality Gate Probability: {quality_probability:.0%}

**Confidence Interval (95%):**
- Lower Bound: ${savings_lower:,.0f}
- Upper Bound: ${savings_upper:,.0f}

**Risk Factors:**
{risk_factors}

**Opportunities:**
{opportunities}

Write a 2-3 paragraph predictive narrative that:
1. Summarizes the year-end outlook with confidence levels
2. Explains key risks that could impact projections
3. Identifies opportunities to improve outcomes
4. Provides specific recommendations for the remaining months"""

CARE_GAP_ANALYSIS_PROMPT = """Analyze care gaps for this member cohort and suggest interventions.

**Cohort:** {cohort_description}
**Members:** {member_count}

**Care Gaps Identified:**
{care_gaps}

**Quality Measures at Risk:**
{at_risk_measures}

Provide:
1. Priority ranking of gaps to address
2. Recommended interventions for each gap
3. Expected impact on quality scores
4. Suggested outreach approach"""

ERROR_EXPLANATION_PROMPT = """Explain this data validation error in plain language and suggest remediation.

**Error Type:** {error_type}
**Dataset:** {dataset}
**Affected Records:** {affected_count} ({affected_pct:.1f}%)
**Details:** {error_details}

Provide:
1. Plain language explanation of what this error means
2. Likely root causes
3. Recommended remediation steps
4. How to prevent this in the future"""
