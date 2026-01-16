# MSSP Analytics Report Generation Prompt

Use this prompt with any LLM to generate a professional HTML consultant report for Medicare Shared Savings Program (MSSP) analytics data.

---

## Instructions

You are a healthcare analytics expert specializing in Medicare Shared Savings Program (MSSP) performance reporting. Your task is to generate a complete, professional HTML report based on the workflow data provided below.

**Generate THREE separate sections of analysis:**

1. **Executive Summary** (3-4 paragraphs): Lead with the most important findings, highlight achievements and concerns, provide actionable recommendations.

2. **Deep Analysis**: Comprehensive analysis of financial and operational metrics, identify main drivers of performance, explain the implications.

3. **Predictive Outlook** (2-3 paragraphs): Year-end projections with confidence levels, key risks and opportunities, specific recommendations for remaining months.

**Then output a COMPLETE HTML file** that includes all three analyses formatted as a professional consultant report.

---

## Workflow Data

```json
{
    "workflow_id": "wf-8bc2b134719a",
    "contract_id": "VBC-MSSP-001",
    "performance_year": 2025,
    "performance_month": 11,
    "status": "completed",
    "financial_metrics": {
        "baseline_spending": 72000000.0,
        "actual_spending": 20038020.43,
        "total_savings": 51961979.57,
        "savings_percentage": 72.17,
        "shared_savings_amount": 25980989.79,
        "baseline_pmpm": 771.31,
        "actual_pmpm": 234.17,
        "target_pmpm": 732.74,
        "member_months": 85569,
        "average_members": 7779,
        "total_admits": 927,
        "total_er_visits": 2478,
        "admits_per_1000": 119.17,
        "er_visits_per_1000": 318.55
    },
    "quality_metrics": {
        "composite_score": 0.0,
        "quality_threshold": 80.0,
        "quality_gate_status": "pending",
        "preventive_care_score": 0.0,
        "chronic_disease_score": 0.0,
        "care_coordination_score": 0.0,
        "patient_experience_score": 0.0
    },
    "risk_metrics": {
        "total_members": 7779,
        "low_risk_count": 2619,
        "medium_risk_count": 3560,
        "high_risk_count": 1600,
        "low_risk_pct": 33.67,
        "medium_risk_pct": 45.76,
        "high_risk_pct": 20.57,
        "average_risk_score": 1.12
    },
    "predictions": {
        "projected_year_end_savings": 51794996.07,
        "projected_shared_savings": 25897498.04,
        "probability_meeting_target": 99.99,
        "probability_quality_gate": 0.0,
        "savings_lower_bound": 37682996.07,
        "savings_upper_bound": 65906996.07,
        "risks": [
            {
                "title": "Quality Gate at Risk",
                "description": "Composite score of 0.0% below 80% threshold",
                "impact": "May not qualify for shared savings distribution"
            }
        ],
        "opportunities": [
            {
                "title": "Strong Savings Performance",
                "description": "Tracking 72.2% below baseline",
                "impact": "Projected shared savings of $25,980,990"
            }
        ]
    }
}
```

---

## Required HTML Output Structure

Generate a complete HTML file with:

1. **Header**: Contract ID, performance period (November 2025), generation date
2. **Navigation**: Links to Overview, Executive Summary, Deep Analysis, Predictions
3. **KPI Cards Section**: Visual cards showing key metrics with color coding (green for good, red for concerns)
4. **Executive Summary Section**: Your 3-4 paragraph executive summary
5. **Deep Analysis Section**: Your comprehensive analysis
6. **Predictive Outlook Section**: Your forward-looking narrative
7. **Footer**: Disclaimer about AI-generated content

**Styling Requirements:**
- Professional consultant report appearance
- Color scheme: Navy blue (#1a365d) primary, with green (#38a169) for positive metrics, red (#e53e3e) for concerns
- Responsive design
- Clean typography with good line height
- KPI cards with left border color indicating status
- Sticky navigation
- Print-friendly

---

## HTML Template

Use this template structure and fill in the `[EXECUTIVE_SUMMARY]`, `[DEEP_ANALYSIS]`, and `[PREDICTIVE_OUTLOOK]` sections with your generated content:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MSSP Analytics Report - VBC-MSSP-001</title>
    <style>
        :root {
            --primary: #1a365d;
            --secondary: #2c5282;
            --accent: #3182ce;
            --success: #38a169;
            --warning: #d69e2e;
            --danger: #e53e3e;
            --light: #f7fafc;
            --dark: #1a202c;
            --gray: #718096;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: var(--dark);
            background: var(--light);
        }

        .container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }

        header {
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            padding: 60px 0 40px;
        }

        .header-content { display: flex; justify-content: space-between; align-items: flex-start; }
        .logo { font-size: 12px; text-transform: uppercase; letter-spacing: 3px; opacity: 0.8; margin-bottom: 10px; }
        h1 { font-size: 2.5rem; font-weight: 300; margin-bottom: 10px; }
        .subtitle { font-size: 1.1rem; opacity: 0.9; }
        .report-meta { text-align: right; font-size: 0.9rem; opacity: 0.9; }
        .report-meta div { margin-bottom: 5px; }

        nav {
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        nav ul { display: flex; list-style: none; }
        nav a {
            display: block;
            padding: 15px 25px;
            color: var(--gray);
            text-decoration: none;
            font-weight: 500;
            border-bottom: 3px solid transparent;
        }
        nav a:hover { color: var(--primary); border-bottom-color: var(--accent); }

        main { padding: 40px 0; }

        section {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 15px rgba(0,0,0,0.05);
            margin-bottom: 30px;
            overflow: hidden;
        }

        .section-header {
            background: var(--primary);
            color: white;
            padding: 20px 30px;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .section-header h2 { font-size: 1.3rem; font-weight: 500; }
        .section-number {
            background: rgba(255,255,255,0.2);
            width: 35px;
            height: 35px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
        }

        .section-content { padding: 30px; }

        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .kpi-card {
            background: var(--light);
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            border-left: 4px solid var(--accent);
        }
        .kpi-card.success { border-left-color: var(--success); }
        .kpi-card.warning { border-left-color: var(--warning); }
        .kpi-card.danger { border-left-color: var(--danger); }

        .kpi-label {
            font-size: 0.85rem;
            color: var(--gray);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        .kpi-value { font-size: 1.8rem; font-weight: 600; color: var(--primary); }
        .kpi-card.success .kpi-value { color: var(--success); }
        .kpi-card.danger .kpi-value { color: var(--danger); }
        .kpi-subtext { font-size: 0.8rem; color: var(--gray); margin-top: 5px; }

        .insight-content { font-size: 1rem; line-height: 1.8; }
        .insight-content p { margin-bottom: 15px; }
        .insight-content h3, .insight-content h4 { color: var(--primary); margin: 25px 0 15px; }
        .insight-content ul { margin: 15px 0; padding-left: 25px; }
        .insight-content li { margin-bottom: 8px; }
        .insight-content strong { color: var(--secondary); }

        .ai-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 20px;
        }

        footer {
            background: var(--dark);
            color: white;
            padding: 40px 0;
            margin-top: 40px;
        }
        .footer-content { display: flex; justify-content: space-between; align-items: center; }
        .footer-disclaimer { font-size: 0.85rem; opacity: 0.7; max-width: 600px; }

        @media (max-width: 768px) {
            .header-content { flex-direction: column; }
            .report-meta { text-align: left; margin-top: 20px; }
            h1 { font-size: 1.8rem; }
            nav ul { flex-wrap: wrap; }
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <div class="header-content">
                <div>
                    <div class="logo">Healthcare Analytics</div>
                    <h1>MSSP Performance Report</h1>
                    <div class="subtitle">Medicare Shared Savings Program Analysis</div>
                </div>
                <div class="report-meta">
                    <div><strong>Contract:</strong> VBC-MSSP-001</div>
                    <div><strong>Period:</strong> November 2025</div>
                    <div><strong>Generated:</strong> [TODAY'S DATE]</div>
                </div>
            </div>
        </div>
    </header>

    <nav>
        <div class="container">
            <ul>
                <li><a href="#overview">Overview</a></li>
                <li><a href="#executive-summary">Executive Summary</a></li>
                <li><a href="#analysis">Deep Analysis</a></li>
                <li><a href="#predictions">Predictions</a></li>
            </ul>
        </div>
    </nav>

    <main>
        <div class="container">
            <!-- KPI Overview -->
            <section id="overview">
                <div class="section-header">
                    <div class="section-number">1</div>
                    <h2>Key Performance Indicators</h2>
                </div>
                <div class="section-content">
                    <div class="kpi-grid">
                        <div class="kpi-card success">
                            <div class="kpi-label">Total Savings</div>
                            <div class="kpi-value">$51,961,980</div>
                            <div class="kpi-subtext">72.2% vs baseline</div>
                        </div>
                        <div class="kpi-card success">
                            <div class="kpi-label">Shared Savings</div>
                            <div class="kpi-value">$25,980,990</div>
                            <div class="kpi-subtext">50% sharing rate</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Actual PMPM</div>
                            <div class="kpi-value">$234.17</div>
                            <div class="kpi-subtext">Target: $732.74</div>
                        </div>
                        <div class="kpi-card danger">
                            <div class="kpi-label">Quality Score</div>
                            <div class="kpi-value">0.0%</div>
                            <div class="kpi-subtext">Threshold: 80%</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Total Members</div>
                            <div class="kpi-value">7,779</div>
                            <div class="kpi-subtext">20.6% high risk</div>
                        </div>
                        <div class="kpi-card warning">
                            <div class="kpi-label">ER Visits / 1000</div>
                            <div class="kpi-value">318.5</div>
                            <div class="kpi-subtext">Utilization metric</div>
                        </div>
                    </div>
                    <div class="kpi-grid">
                        <div class="kpi-card">
                            <div class="kpi-label">Baseline Spending</div>
                            <div class="kpi-value">$72,000,000</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Actual Spending</div>
                            <div class="kpi-value">$20,038,020</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Admits / 1000</div>
                            <div class="kpi-value">119.2</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Avg Risk Score</div>
                            <div class="kpi-value">1.12</div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Executive Summary -->
            <section id="executive-summary">
                <div class="section-header">
                    <div class="section-number">2</div>
                    <h2>Executive Summary</h2>
                </div>
                <div class="section-content">
                    <div class="ai-badge">AI-Generated Analysis</div>
                    <div class="insight-content">
                        [EXECUTIVE_SUMMARY]
                    </div>
                </div>
            </section>

            <!-- Deep Analysis -->
            <section id="analysis">
                <div class="section-header">
                    <div class="section-number">3</div>
                    <h2>Deep Analysis</h2>
                </div>
                <div class="section-content">
                    <div class="ai-badge">AI-Generated Analysis</div>
                    <div class="insight-content">
                        [DEEP_ANALYSIS]
                    </div>
                </div>
            </section>

            <!-- Predictions -->
            <section id="predictions">
                <div class="section-header">
                    <div class="section-number">4</div>
                    <h2>Predictive Outlook</h2>
                </div>
                <div class="section-content">
                    <div class="ai-badge">AI-Generated Analysis</div>
                    <div class="insight-content">
                        [PREDICTIVE_OUTLOOK]
                    </div>
                </div>
            </section>
        </div>
    </main>

    <footer>
        <div class="container">
            <div class="footer-content">
                <div class="footer-disclaimer">
                    <strong>Disclaimer:</strong> This report was generated using AI-powered analytics.
                    All insights should be reviewed by qualified healthcare professionals before
                    making operational decisions.
                </div>
            </div>
        </div>
    </footer>
</body>
</html>
```

---

## Output Format

Replace the placeholders in the HTML template:
- `[TODAY'S DATE]` → Current date in "Month DD, YYYY" format
- `[EXECUTIVE_SUMMARY]` → Your 3-4 paragraph executive summary in HTML (use `<p>`, `<strong>`, `<ul>`, `<li>` tags)
- `[DEEP_ANALYSIS]` → Your comprehensive analysis in HTML
- `[PREDICTIVE_OUTLOOK]` → Your predictive narrative in HTML

**Output the complete HTML file with no markdown code blocks - just the raw HTML.**
