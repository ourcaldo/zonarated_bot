"""Async PostgreSQL connection pool (asyncpg)."""

from __future__ import annotations

import asyncpg

from bot.config import settings

_pool: asyncpg.Pool | None = None


async def create_pool() -> asyncpg.Pool:
    """Create and cache the connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=2,
            max_size=10,
        )
    return _pool


async def get_pool() -> asyncpg.Pool:
    """Return the existing pool (create if needed)."""
    if _pool is None:
        return await create_pool()
    return _pool


async def close_pool() -> None:
    """Gracefully close all connections."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
