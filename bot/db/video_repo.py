"""Repository for the `videos` and download-related tables."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import asyncpg


# ──────────────────────────────────────────────
# Video code generation
# ──────────────────────────────────────────────

async def generate_video_code(pool: asyncpg.Pool, genre_name: str) -> str:
    """Generate a unique video code like A-2943 or AC-2949.

    Format: {prefix}-{4 random digits}
    The prefix is read from the topics table (stored on genre creation).
    When category contains multiple genres (comma-separated), uses the first one.
    """
    # Extract the first genre name if comma-separated
    first_genre = genre_name.split(",")[0].strip()

    # Look up the stored prefix for this genre
    prefix = await pool.fetchval(
        "SELECT prefix FROM topics WHERE LOWER(name) = LOWER($1)", first_genre
    )
    if not prefix:
        # Fallback: first letter uppercase
        prefix = first_genre[0].upper() if first_genre else "X"

    for _ in range(100):  # max attempts
        digits = random.randint(1000, 9999)
        code = f"{prefix}-{digits}"
        # Check uniqueness
        existing = await pool.fetchval(
            "SELECT 1 FROM videos WHERE code = $1", code
        )
        if not existing:
            return code

    raise ValueError("Could not generate unique video code after 100 attempts")


# ──────────────────────────────────────────────
# Videos CRUD
# ──────────────────────────────────────────────

async def create_video(
    pool: asyncpg.Pool,
    title: str,
    category: str,
    description: Optional[str],
    file_url: str,
    topic_id: Optional[int] = None,
    message_id: Optional[int] = None,
    affiliate_link: Optional[str] = None,
) -> asyncpg.Record:
    """Insert a new video record with auto-generated code. Returns the created row."""
    code = await generate_video_code(pool, category)
    return await pool.fetchrow(
        """
        INSERT INTO videos
            (code, title, category, description, file_url, topic_id, message_id, affiliate_link)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING *
        """,
        code,
        title,
        category,
        description,
        file_url,
        topic_id,
        message_id,
        affiliate_link,
    )


async def get_video(pool: asyncpg.Pool, video_id: int) -> Optional[asyncpg.Record]:
    """Fetch a single video by ID."""
    return await pool.fetchrow(
        "SELECT * FROM videos WHERE video_id = $1", video_id
    )


async def get_video_by_code(pool: asyncpg.Pool, code: str) -> Optional[asyncpg.Record]:
    """Fetch a single video by its unique code (case-insensitive)."""
    return await pool.fetchrow(
        "SELECT * FROM videos WHERE UPPER(code) = UPPER($1)", code
    )


async def set_message_id(
    pool: asyncpg.Pool, video_id: int, message_id: int, topic_id: Optional[int] = None
) -> None:
    """Update the Telegram message_id (and optionally topic_id) after posting."""
    await pool.execute(
        """
        UPDATE videos
        SET message_id = $2, topic_id = COALESCE($3, topic_id)
        WHERE video_id = $1
        """,
        video_id,
        message_id,
        topic_id,
    )


async def set_thumbnail_file_id(
    pool: asyncpg.Pool, video_id: int, thumbnail_file_id: str
) -> None:
    """Store the Telegram file_id for the video thumbnail photo."""
    await pool.execute(
        "UPDATE videos SET thumbnail_file_id = $2 WHERE video_id = $1",
        video_id,
        thumbnail_file_id,
    )


async def set_shortened_url(
    pool: asyncpg.Pool, video_id: int, shortened_url: str
) -> None:
    """Store the shortened URL for a video."""
    await pool.execute(
        "UPDATE videos SET shortened_url = $2 WHERE video_id = $1",
        video_id,
        shortened_url,
    )


async def increment_views(pool: asyncpg.Pool, video_id: int) -> None:
    """Increment the view counter by 1."""
    await pool.execute(
        "UPDATE videos SET views = views + 1 WHERE video_id = $1", video_id
    )


async def increment_downloads(pool: asyncpg.Pool, video_id: int) -> None:
    """Increment the download counter by 1."""
    await pool.execute(
        "UPDATE videos SET downloads = downloads + 1 WHERE video_id = $1", video_id
    )


async def get_video_count(pool: asyncpg.Pool) -> int:
    """Total number of videos."""
    return await pool.fetchval("SELECT COUNT(*) FROM videos") or 0


async def get_recent_videos(pool: asyncpg.Pool, limit: int = 10) -> list[asyncpg.Record]:
    """Get the most recent videos."""
    return await pool.fetch(
        "SELECT * FROM videos ORDER BY post_date DESC LIMIT $1", limit
    )


# ──────────────────────────────────────────────
# Download sessions
# ──────────────────────────────────────────────

async def create_download_session(
    pool: asyncpg.Pool,
    user_id: int,
    video_id: int,
    expires_minutes: int = 10,
) -> str:
    """Create a download session and return its session_id."""
    session_id = uuid.uuid4().hex[:16]
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    await pool.execute(
        """
        INSERT INTO download_sessions (session_id, user_id, video_id, expires_at)
        VALUES ($1, $2, $3, $4)
        """,
        session_id,
        user_id,
        video_id,
        expires_at,
    )
    return session_id


async def get_download_session(
    pool: asyncpg.Pool, session_id: str
) -> Optional[asyncpg.Record]:
    """Fetch a download session by ID."""
    return await pool.fetchrow(
        "SELECT * FROM download_sessions WHERE session_id = $1", session_id
    )


async def mark_visited(pool: asyncpg.Pool, session_id: str) -> None:
    """Mark that the user has physically visited the redirect link."""
    await pool.execute(
        "UPDATE download_sessions SET visited_at = NOW() WHERE session_id = $1",
        session_id,
    )


async def mark_affiliate_visited(pool: asyncpg.Pool, session_id: str) -> None:
    """Mark that the user has visited the affiliate link."""
    await pool.execute(
        "UPDATE download_sessions SET affiliate_visited = TRUE WHERE session_id = $1",
        session_id,
    )


async def mark_video_sent(pool: asyncpg.Pool, session_id: str) -> None:
    """Mark that the video has been delivered to the user."""
    await pool.execute(
        "UPDATE download_sessions SET video_sent = TRUE WHERE session_id = $1",
        session_id,
    )


async def get_active_session(
    pool: asyncpg.Pool, user_id: int, video_id: int
) -> Optional[asyncpg.Record]:
    """Get an active (non-expired) session for this user+video combo."""
    return await pool.fetchrow(
        """
        SELECT * FROM download_sessions
        WHERE user_id = $1
          AND video_id = $2
          AND expires_at > NOW()
          AND video_sent = FALSE
        ORDER BY created_at DESC
        LIMIT 1
        """,
        user_id,
        video_id,
    )


# ──────────────────────────────────────────────
# Downloads log
# ──────────────────────────────────────────────

async def log_download(
    pool: asyncpg.Pool,
    user_id: int,
    video_id: int,
    session_id: str,
    affiliate_clicked: bool,
) -> None:
    """Record a completed download in the permanent log."""
    await pool.execute(
        """
        INSERT INTO downloads
            (user_id, video_id, session_id, affiliate_link_clicked,
             download_completed, download_date)
        VALUES ($1, $2, $3, $4, TRUE, NOW())
        """,
        user_id,
        video_id,
        session_id,
        affiliate_clicked,
    )


async def get_download_stats(pool: asyncpg.Pool) -> dict:
    """Get aggregate download statistics."""
    row = await pool.fetchrow(
        """
        SELECT
            COUNT(*)                                          AS total_downloads,
            COUNT(*) FILTER (WHERE affiliate_link_clicked)    AS affiliate_clicks,
            COUNT(DISTINCT user_id)                           AS unique_users,
            COUNT(DISTINCT video_id)                          AS unique_videos
        FROM downloads
        WHERE download_completed = TRUE
        """
    )
    if row:
        return dict(row)
    return {
        "total_downloads": 0,
        "affiliate_clicks": 0,
        "unique_users": 0,
        "unique_videos": 0,
    }
