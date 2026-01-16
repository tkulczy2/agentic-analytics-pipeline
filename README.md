# Agentic Analytics Pipeline

> **[View Next Steps: LLM Capabilities Expansion Plan](next_steps/README.md)** - Detailed implementation plan for 10 additional LLM-powered features

A production-ready autonomous analytics pipeline for Medicare Shared Savings Program (MSSP) value-based care contracts. This system demonstrates end-to-end automation from data extraction through executive reporting using a multi-agent architecture.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                        │
│  (Coordinates all agents, manages state, handles errors)    │
└──────────────┬──────────────────────────────────────────────┘
               │
       ┌───────┴────────┬──────────────┬──────────────┐
       │                │              │              │
   ┌───▼────┐     ┌────▼─────┐   ┌───▼────┐    ┌───▼────┐
   │ DATA   │     │VALIDATION│   │ANALYSIS│    │REPORTING│
   │ AGENT  │────▶│  AGENT   │──▶│ AGENT  │───▶│  AGENT  │
   └────────┘     └──────────┘   └────────┘    └─────────┘
                                                     │
                                               ┌─────▼─────┐
                                               │ INSIGHTS  │
                                               │   AGENT   │
                                               │   (LLM)   │
                                               └───────────┘
```

### Agents

1. **Orchestrator Agent**: Master controller that coordinates all agents, manages workflow state, and handles failures with retry logic.

2. **Data Extraction Agent**: Extracts healthcare data from PostgreSQL with intelligent query optimization, connection pooling, and incremental/full refresh decision logic.

3. **Validation Agent**: Comprehensive data quality checks with automatic remediation of common issues (duplicates, negative amounts, date typos, gender mismatches).

4. **Analysis Agent**: Calculates MSSP financial metrics, quality scores, risk stratification, and predictive analytics.

5. **Reporting Agent**: Generates PowerPoint executive reports and distributes via email to appropriate stakeholders.

6. **Insights Agent** (LLM-powered): Generates executive summaries, predictive narratives, answers natural language queries, and explains validation errors using Claude, OpenAI, or local models via Ollama.

## Features

- **Autonomous Execution**: Complete end-to-end workflow without manual intervention
- **State Persistence**: Workflow state survives container restarts (Redis)
- **Auto-Remediation**: Automatic fixing of common data quality issues
- **Retry Logic**: Exponential backoff for transient failures
- **Email Notifications**: Automatic notifications on completion/failure
- **REST API**: Full workflow management via FastAPI endpoints
- **Comprehensive Testing**: Unit and integration test suites
- **LLM-Powered Insights**: Executive summaries, natural language queries, and predictive narratives via Claude, OpenAI, or Ollama

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)

### 1. Start the Infrastructure

```bash
cd agentic-analytics-pipeline
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- MailHog (SMTP: 1025, Web UI: 8025)
- API Server (port 8000)
- pgAdmin (port 8080)
- Redis Commander (port 8081)

### 2. Generate Test Data

```bash
# Via API
curl -X POST http://localhost:8000/test-data/generate \
  -H "Content-Type: application/json" \
  -d '{
    "num_members": 12000,
    "num_medical_claims": 50000,
    "num_pharmacy_claims": 15000,
    "include_duplicates": true,
    "include_negative_amounts": true
  }'

# Or run the script directly
docker-compose exec api python scripts/generate_test_data.py
```

### 3. Start a Workflow

```bash
curl -X POST http://localhost:8000/workflows/ \
  -H "Content-Type: application/json" \
  -d '{
    "contract_id": "VBC-MSSP-001",
    "performance_year": 2024,
    "performance_month": 11
  }'
```

### 4. Check Workflow Status

```bash
curl http://localhost:8000/workflows/{workflow_id}
```

### 5. View Results

- **Email**: Open http://localhost:8025 to see email notifications
- **Reports**: Generated PowerPoint files are in `/app/reports/`
- **Database**: Access pgAdmin at http://localhost:8080
- **State**: View Redis data at http://localhost:8081

## API Endpoints

### Workflow Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/workflows/` | Start a new analytics workflow |
| GET | `/workflows/{id}` | Get workflow status and results |
| GET | `/workflows/{id}/logs` | Get workflow execution logs |
| POST | `/workflows/{id}/pause` | Pause a running workflow |
| POST | `/workflows/{id}/resume` | Resume a paused workflow |
| POST | `/workflows/{id}/cancel` | Cancel a workflow |
| GET | `/contracts/{id}/workflows` | List all workflows for a contract |
| GET | `/health` | System health check |
| POST | `/test-data/generate` | Generate test data |

### LLM Insights

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/insights/query` | Ask natural language questions about the data |
| GET | `/insights/summary/{id}` | Generate executive summary for a workflow |
| GET | `/insights/predictions/{id}` | Generate predictive narrative for a workflow |
| POST | `/insights/explain-error` | Get plain-language explanation of validation errors |
| GET | `/insights/providers` | Check status of available LLM providers |

## Configuration

Environment variables:

```bash
# Database & Infrastructure
DATABASE_URL=postgresql://analytics:analytics_password@postgres:5432/healthcare_analytics
REDIS_URL=redis://redis:6379/0
SMTP_HOST=mailhog
SMTP_PORT=1025
DATA_DIR=/app/data
REPORTS_DIR=/app/reports

# LLM Providers (set in your shell environment)
ANTHROPIC_API_KEY=sk-ant-...    # For Claude (default provider)
OPENAI_API_KEY=sk-proj-...      # For OpenAI GPT models
OLLAMA_BASE_URL=http://localhost:11434  # For local Ollama models
```

## Project Structure

```
agentic-analytics-pipeline/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── README.md
├── src/
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Configuration
│   ├── agents/
│   │   ├── base.py             # BaseAgent class
│   │   ├── orchestrator.py     # Orchestrator Agent
│   │   ├── data_extraction.py  # Data Extraction Agent
│   │   ├── validation.py       # Validation Agent
│   │   ├── analysis.py         # Analysis Agent
│   │   ├── reporting.py        # Reporting Agent
│   │   └── insights.py         # Insights Agent (LLM)
│   ├── models/
│   │   ├── workflow.py         # WorkflowState, AgentStatus
│   │   ├── financial.py        # FinancialMetrics
│   │   ├── quality.py          # QualityMetrics
│   │   ├── risk.py             # RiskStratification
│   │   └── predictions.py      # Predictions
│   ├── services/
│   │   ├── state_manager.py    # Redis state persistence
│   │   ├── database.py         # PostgreSQL connection
│   │   ├── email_service.py    # SMTP email
│   │   ├── report_generator.py # PowerPoint generation
│   │   └── llm/                # LLM Service
│   │       ├── base.py         # Provider abstraction
│   │       ├── service.py      # Main LLM service
│   │       ├── prompts.py      # Prompt templates
│   │       └── providers/      # Claude, OpenAI, Ollama
│   ├── validation/
│   │   ├── rules.py            # Validation rules
│   │   └── remediation.py      # Auto-remediation
│   └── api/
│       ├── routes.py           # API endpoints
│       └── schemas.py          # Pydantic models
├── tests/
│   ├── conftest.py
│   ├── test_unit/
│   └── test_integration/
├── scripts/
│   ├── generate_test_data.py
│   ├── init_db.sql
│   └── run_demo.py
├── data/
└── reports/
```

## Running Tests

```bash
# Unit tests
pytest tests/test_unit/ -v

# Integration tests (requires Docker services)
pytest tests/test_integration/ -v

# All tests with coverage
pytest --cov=src tests/
```

## Demo

Run the complete demo:

```bash
docker-compose exec api python scripts/run_demo.py
```

This will:
1. Generate test data with intentional quality issues
2. Start and monitor a complete workflow
3. Display results including financial metrics, quality scores, and predictions

## Metrics Calculated

### Financial Metrics
- Actual vs Baseline spending
- Total savings and savings percentage
- Shared savings amount
- PMPM (Per Member Per Month) metrics
- Utilization rates (ER visits, admits per 1000)

### Quality Metrics
- Composite quality score (weighted)
- Category scores: Preventive Care, Chronic Disease, Care Coordination, Patient Experience
- Quality gate status: Eligible, At Risk, Ineligible

### Risk Stratification
- Member counts by risk category (Low, Medium, High)
- PMPM by risk category
- Average HCC risk score

### Predictions
- Year-end spending projection
- Probability of meeting savings target
- Identified risks and opportunities
- Recommended actions

## LLM-Powered Insights

The Insights Agent uses large language models to generate human-readable analysis from workflow data.

### Supported Providers

| Provider | Default Model | Configuration |
|----------|---------------|---------------|
| Claude (default) | claude-sonnet-4-20250514 | `ANTHROPIC_API_KEY` |
| OpenAI | gpt-4o | `OPENAI_API_KEY` |
| Ollama | llama3.1 | `OLLAMA_BASE_URL` |

### Features

**Executive Summary** (`GET /insights/summary/{workflow_id}`)

Generates a 3-4 paragraph executive summary covering:
- Financial performance and key drivers
- Quality performance highlights and concerns
- Risk profile and utilization patterns
- Recommendations for the coming period

**Predictive Narrative** (`GET /insights/predictions/{workflow_id}`)

Generates forward-looking analysis including:
- Year-end outlook with confidence levels
- Key risks that could impact projections
- Opportunities to improve outcomes
- Specific recommendations for remaining months

**Natural Language Queries** (`POST /insights/query`)

Ask questions about the data in plain English:

```bash
curl -X POST http://localhost:8000/insights/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is driving our savings this quarter?",
    "workflow_id": "wf-abc123",
    "provider": "claude"
  }'
```

**Error Explanations** (`POST /insights/explain-error`)

Get plain-language explanations of validation errors with remediation suggestions.

### Switching Providers

All insight endpoints accept `provider` and `model` parameters:

```bash
# Use OpenAI instead of Claude
curl "http://localhost:8000/insights/summary/wf-abc123?provider=openai"

# Use a specific model
curl "http://localhost:8000/insights/summary/wf-abc123?provider=openai&model=gpt-4-turbo"

# Use local Ollama
curl "http://localhost:8000/insights/summary/wf-abc123?provider=ollama&model=llama3.2"
```

## Validation Rules

| Rule | Severity | Auto-Fixable |
|------|----------|--------------|
| Required fields present | CRITICAL | No |
| Null values (<5% = warning) | CRITICAL/WARNING | No |
| Age 0-120 years | CRITICAL | No |
| Cost amounts reasonable | WARNING | Conditional |
| Service date before paid date | CRITICAL | No |
| No future service dates | CRITICAL | Yes (year typos) |
| Gender-diagnosis consistency | CRITICAL | Yes (<10 records) |
| Duplicates (<5% = auto-fix) | CRITICAL/WARNING | Conditional |

## License

MIT License
