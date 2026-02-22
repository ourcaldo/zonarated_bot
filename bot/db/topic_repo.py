"""Repository for the `topics` table — genre forum topics."""

from __future__ import annotations

from typing import Optional

import asyncpg


# ──────────────────────────────────────────────
# Prefix generation
# ──────────────────────────────────────────────

async def generate_prefix(pool: asyncpg.Pool, name: str) -> str:
    """Generate a unique prefix for a genre name.

    Logic:
        1. Try the first letter (uppercase): e.g. Asia → A
        2. If taken, try first 2 letters: e.g. Action → AC
        3. If taken, try first 3 letters: e.g. Adventure → AD (wait, AD)...
        4. Keep extending until unique (up to full name)
    """
    name_upper = name.upper()
    for length in range(1, len(name_upper) + 1):
        candidate = name_upper[:length]
        existing = await pool.fetchval(
            "SELECT 1 FROM topics WHERE prefix = $1", candidate
        )
        if not existing:
            return candidate
    # Fallback: append a number
    for i in range(2, 100):
        candidate = f"{name_upper[:2]}{i}"
        existing = await pool.fetchval(
            "SELECT 1 FROM topics WHERE prefix = $1", candidate
        )
        if not existing:
            return candidate
    raise ValueError(f"Could not generate unique prefix for '{name}'")


# ──────────────────────────────────────────────
# CRUD
# ──────────────────────────────────────────────

async def create_topic(
    pool: asyncpg.Pool,
    name: str,
    thread_id: Optional[int] = None,
    is_all: bool = False,
) -> asyncpg.Record:
    """Insert a new genre topic with auto-generated prefix. Returns the created row."""
    prefix = await generate_prefix(pool, name)
    return await pool.fetchrow(
        """
        INSERT INTO topics (name, prefix, thread_id, is_all)
        VALUES ($1, $2, $3, $4)
        RETURNING *
        """,
        name,
        prefix,
        thread_id,
        is_all,
    )


async def get_all_topics(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    """Return all topics ordered by name."""
    return await pool.fetch(
        "SELECT * FROM topics ORDER BY is_all DESC, name ASC"
    )


async def get_topic_by_name(pool: asyncpg.Pool, name: str) -> Optional[asyncpg.Record]:
    """Fetch a topic by its genre name (case-insensitive)."""
    return await pool.fetchrow(
        "SELECT * FROM topics WHERE LOWER(name) = LOWER($1)", name
    )


async def get_topic_by_id(pool: asyncpg.Pool, topic_id: int) -> Optional[asyncpg.Record]:
    """Fetch a topic by its internal ID."""
    return await pool.fetchrow(
        "SELECT * FROM topics WHERE topic_id = $1", topic_id
    )


async def get_all_topic(pool: asyncpg.Pool) -> Optional[asyncpg.Record]:
    """Fetch the special 'All Videos' topic."""
    return await pool.fetchrow(
        "SELECT * FROM topics WHERE is_all = TRUE LIMIT 1"
    )


async def set_thread_id(pool: asyncpg.Pool, topic_id: int, thread_id: int) -> None:
    """Update the Telegram thread_id after creating the forum topic."""
    await pool.execute(
        "UPDATE topics SET thread_id = $2 WHERE topic_id = $1",
        topic_id,
        thread_id,
    )


async def delete_topic(pool: asyncpg.Pool, topic_id: int) -> bool:
    """Delete a topic by ID. Returns True if a row was deleted."""
    result = await pool.execute(
        "DELETE FROM topics WHERE topic_id = $1", topic_id
    )
    return result == "DELETE 1"


async def get_topic_count(pool: asyncpg.Pool) -> int:
    """Return the total number of topics."""
    return await pool.fetchval("SELECT COUNT(*) FROM topics") or 0
