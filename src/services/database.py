"""PostgreSQL database service with connection pooling."""
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import QueuePool

from src.config import settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """Database service with connection pooling and health checks."""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize the database service."""
        self.database_url = database_url or settings.database_url

        # Convert postgresql:// to postgresql+asyncpg:// for async
        if self.database_url.startswith("postgresql://"):
            self.async_url = self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://"
            )
        else:
            self.async_url = self.database_url

        # Sync engine for pandas operations
        self._sync_engine = None

        # Async engine for async operations
        self._async_engine = None
        self._async_session_factory = None

    def _get_sync_engine(self):
        """Get or create synchronous engine for pandas operations."""
        if self._sync_engine is None:
            self._sync_engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
            )
        return self._sync_engine

    async def connect(self):
        """Initialize async connection pool."""
        if self._async_engine is None:
            self._async_engine = create_async_engine(
                self.async_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
            )
            self._async_session_factory = async_sessionmaker(
                self._async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            logger.info("Database connection pool initialized")

    async def disconnect(self):
        """Close the connection pool."""
        if self._async_engine:
            await self._async_engine.dispose()
            self._async_engine = None
            self._async_session_factory = None
            logger.info("Database connection pool closed")

        if self._sync_engine:
            self._sync_engine.dispose()
            self._sync_engine = None

    async def health_check(self) -> bool:
        """Check if database is accessible."""
        try:
            await self.connect()
            async with self._async_session_factory() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    @asynccontextmanager
    async def session(self):
        """Get an async database session."""
        await self.connect()
        async with self._async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def read_sql(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame."""
        engine = self._get_sync_engine()
        with engine.connect() as conn:
            return pd.read_sql(text(query), conn, params=params)

    async def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a SQL query asynchronously."""
        await self.connect()
        async with self._async_session_factory() as session:
            result = await session.execute(text(query), params or {})
            await session.commit()
            return result

    async def execute_many(self, query: str, params_list: List[Dict[str, Any]]) -> None:
        """Execute a SQL query with multiple parameter sets."""
        await self.connect()
        async with self._async_session_factory() as session:
            for params in params_list:
                await session.execute(text(query), params)
            await session.commit()

    async def get_table_count(self, table_name: str) -> int:
        """Get the row count of a table."""
        result = await self.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
        row = result.fetchone()
        return row[0] if row else 0

    async def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get the schema of a table."""
        query = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = :table_name
            ORDER BY ordinal_position
        """
        result = await self.execute(query, {"table_name": table_name})
        rows = result.fetchall()
        return [
            {
                "column_name": row[0],
                "data_type": row[1],
                "is_nullable": row[2],
                "column_default": row[3],
            }
            for row in rows
        ]

    async def truncate_table(self, table_name: str) -> None:
        """Truncate a table."""
        await self.execute(f"TRUNCATE TABLE {table_name} CASCADE")
        logger.info(f"Truncated table: {table_name}")

    async def insert_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        if_exists: str = "append"
    ) -> int:
        """Insert a DataFrame into a table."""
        engine = self._get_sync_engine()
        rows = df.to_sql(
            table_name,
            engine,
            if_exists=if_exists,
            index=False,
            method="multi",
            chunksize=1000,
        )
        logger.info(f"Inserted {len(df)} rows into {table_name}")
        return len(df)
