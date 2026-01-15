"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Agentic Analytics Pipeline API")
    yield
    logger.info("Shutting down Agentic Analytics Pipeline API")


app = FastAPI(
    title="Agentic Analytics Pipeline",
    description="""
    Autonomous analytics pipeline for Medicare Shared Savings Program (MSSP)
    value-based care contracts.

    This API provides endpoints for:
    - Starting and managing analytics workflows
    - Monitoring workflow execution and viewing logs
    - Generating test data for development and testing
    - Health checks for system dependencies

    The pipeline consists of four agents:
    1. **Data Extraction Agent**: Extracts healthcare data from PostgreSQL
    2. **Validation Agent**: Validates data quality with auto-remediation
    3. **Analysis Agent**: Calculates financial, quality, and risk metrics
    4. **Reporting Agent**: Generates PowerPoint reports and sends emails
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/", tags=["root"])
async def root():
    """API root endpoint."""
    return {
        "name": "Agentic Analytics Pipeline",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
