"""Repository for the `users` table."""

from __future__ import annotations

from typing import Any, Optional

import asyncpg


# ──────────────────────────────────────────────
# Create / Get
# ──────────────────────────────────────────────

async def get_user(pool: asyncpg.Pool, user_id: int) -> Optional[asyncpg.Record]:
    """Fetch a single user by Telegram user ID."""
    return await pool.fetchrow(
        "SELECT * FROM users WHERE user_id = $1", user_id
    )


async def create_user(
    pool: asyncpg.Pool,
    user_id: int,
    username: Optional[str],
    first_name: Optional[str],
    referral_link: str,
    referred_by: Optional[int] = None,
) -> asyncpg.Record:
    """Insert a new user. Returns the created row. Ignores if exists."""
    return await pool.fetchrow(
        """
        INSERT INTO users (user_id, username, first_name, referral_link, referred_by)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (user_id) DO UPDATE
            SET username   = COALESCE(EXCLUDED.username, users.username),
                first_name = COALESCE(EXCLUDED.first_name, users.first_name),
                last_updated = NOW()
        RETURNING *
        """,
        user_id,
        username,
        first_name,
        referral_link,
        referred_by,
    )


# ──────────────────────────────────────────────
# Referral helpers
# ──────────────────────────────────────────────

async def get_referral_count(pool: asyncpg.Pool, user_id: int) -> int:
    """Get the number of people this user has referred."""
    val = await pool.fetchval(
        "SELECT referral_count FROM users WHERE user_id = $1", user_id
    )
    return val or 0


async def increment_referral_count(pool: asyncpg.Pool, user_id: int) -> int:
    """Increment referral_count by 1 and return the new value."""
    return await pool.fetchval(
        """
        UPDATE users
        SET referral_count = referral_count + 1,
            last_updated = NOW()
        WHERE user_id = $1
        RETURNING referral_count
        """,
        user_id,
    )


# ──────────────────────────────────────────────
# Verification / approval flags
# ──────────────────────────────────────────────

async def set_verification_complete(pool: asyncpg.Pool, user_id: int) -> None:
    """Mark the user as fully verified."""
    await pool.execute(
        """
        UPDATE users
        SET verification_complete = TRUE,
            approved = TRUE,
            last_updated = NOW()
        WHERE user_id = $1
        """,
        user_id,
    )


async def set_ready_to_join(pool: asyncpg.Pool, user_id: int, ready: bool) -> None:
    """Toggle the temporary ready_to_join flag."""
    await pool.execute(
        """
        UPDATE users
        SET ready_to_join = $2,
            last_updated = NOW()
        WHERE user_id = $1
        """,
        user_id,
        ready,
    )


async def set_joined_supergroup(pool: asyncpg.Pool, user_id: int) -> None:
    """Mark user as having successfully joined the supergroup."""
    await pool.execute(
        """
        UPDATE users
        SET joined_supergroup = TRUE,
            ready_to_join = FALSE,
            last_updated = NOW()
        WHERE user_id = $1
        """,
        user_id,
    )


async def is_verified(pool: asyncpg.Pool, user_id: int) -> bool:
    """Check if user has completed verification."""
    val = await pool.fetchval(
        "SELECT verification_complete FROM users WHERE user_id = $1", user_id
    )
    return bool(val)


async def is_ready_to_join(pool: asyncpg.Pool, user_id: int) -> bool:
    """Check the ready_to_join flag."""
    val = await pool.fetchval(
        "SELECT ready_to_join FROM users WHERE user_id = $1", user_id
    )
    return bool(val)


async def is_approved(pool: asyncpg.Pool, user_id: int) -> bool:
    """Check the approved flag."""
    val = await pool.fetchval(
        "SELECT approved FROM users WHERE user_id = $1", user_id
    )
    return bool(val)


# ──────────────────────────────────────────────
# Stats (for admin)
# ──────────────────────────────────────────────

async def get_language(pool: asyncpg.Pool, user_id: int) -> str | None:
    """Get user's language preference. Returns None if not set."""
    return await pool.fetchval(
        "SELECT language FROM users WHERE user_id = $1", user_id
    )


async def set_language(pool: asyncpg.Pool, user_id: int, lang: str) -> None:
    """Set user's language preference ('id' or 'en')."""
    await pool.execute(
        """
        UPDATE users
        SET language = $2,
            last_updated = NOW()
        WHERE user_id = $1
        """,
        user_id,
        lang,
    )


async def get_user_stats(pool: asyncpg.Pool) -> dict[str, Any]:
    """Get aggregate user statistics."""
    row = await pool.fetchrow(
        """
        SELECT
            COUNT(*)                                    AS total_users,
            COUNT(*) FILTER (WHERE verification_complete)  AS verified_users,
            COUNT(*) FILTER (WHERE joined_supergroup)      AS joined_users
        FROM users
        """
    )
    return dict(row) if row else {"total_users": 0, "verified_users": 0, "joined_users": 0}
