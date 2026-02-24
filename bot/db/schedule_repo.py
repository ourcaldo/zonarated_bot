"""Repository for the `scheduled_videos` table."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import asyncpg


async def create_scheduled_video(
    pool: asyncpg.Pool,
    title: str,
    category: str | None,
    description: str | None,
    file_url: str,
    thumbnail_b64: str | None,
    thumbnail_file_id: str | None,
    affiliate_link: str | None,
    topic_ids: str,
    scheduled_at: datetime,
    created_by: int,
) -> asyncpg.Record:
    """Insert a new scheduled video entry."""
    return await pool.fetchrow(
        """
        INSERT INTO scheduled_videos
            (title, category, description, file_url, thumbnail_b64,
             thumbnail_file_id, affiliate_link, topic_ids,
             scheduled_at, created_by)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING *
        """,
        title,
        category,
        description,
        file_url,
        thumbnail_b64,
        thumbnail_file_id,
        affiliate_link,
        topic_ids,
        scheduled_at,
        created_by,
    )


async def get_pending_videos(pool: asyncpg.Pool, limit: int = 5) -> list[asyncpg.Record]:
    """Fetch scheduled videos that are due for posting."""
    return await pool.fetch(
        """
        SELECT * FROM scheduled_videos
        WHERE status = 'pending'
          AND scheduled_at <= NOW()
        ORDER BY scheduled_at ASC
        LIMIT $1
        """,
        limit,
    )


async def update_schedule_status(
    pool: asyncpg.Pool,
    schedule_id: int,
    status: str,
    error: str | None = None,
) -> None:
    """Update the status of a scheduled video."""
    if status == "posted":
        await pool.execute(
            """
            UPDATE scheduled_videos
            SET status = $2, posted_at = NOW()
            WHERE schedule_id = $1
            """,
            schedule_id,
            status,
        )
    elif error:
        await pool.execute(
            """
            UPDATE scheduled_videos
            SET status = $2, error_message = $3
            WHERE schedule_id = $1
            """,
            schedule_id,
            status,
            error,
        )
    else:
        await pool.execute(
            "UPDATE scheduled_videos SET status = $2 WHERE schedule_id = $1",
            schedule_id,
            status,
        )


async def get_upcoming_schedules(pool: asyncpg.Pool, limit: int = 20) -> list[asyncpg.Record]:
    """Get upcoming and recent scheduled videos for the admin queue view."""
    return await pool.fetch(
        """
        SELECT * FROM scheduled_videos
        ORDER BY
            CASE status
                WHEN 'pending' THEN 0
                WHEN 'posting' THEN 1
                WHEN 'posted' THEN 2
                WHEN 'failed' THEN 3
                WHEN 'cancelled' THEN 4
            END,
            scheduled_at ASC
        LIMIT $1
        """,
        limit,
    )


async def cancel_schedule(pool: asyncpg.Pool, schedule_id: int) -> bool:
    """Cancel a pending scheduled video. Returns True if successful."""
    result = await pool.execute(
        """
        UPDATE scheduled_videos
        SET status = 'cancelled'
        WHERE schedule_id = $1 AND status = 'pending'
        """,
        schedule_id,
    )
    return result == "UPDATE 1"


async def get_scheduled_urls(pool: asyncpg.Pool) -> set[str]:
    """Return all file_url values of pending/posting scheduled videos.

    Used for exclusion in Auto Get & Run.
    """
    rows = await pool.fetch(
        "SELECT file_url FROM scheduled_videos WHERE status IN ('pending', 'posting')"
    )
    return {r["file_url"] for r in rows}


async def get_schedule_by_id(pool: asyncpg.Pool, schedule_id: int) -> Optional[asyncpg.Record]:
    """Fetch a scheduled video by ID."""
    return await pool.fetchrow(
        "SELECT * FROM scheduled_videos WHERE schedule_id = $1", schedule_id
    )
