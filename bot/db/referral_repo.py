"""Repository for the `referrals` table."""

from __future__ import annotations

from typing import Optional

import asyncpg


async def referral_exists(
    pool: asyncpg.Pool, referrer_id: int, referred_id: int
) -> bool:
    """Check if this referral pair already exists (prevent double-count)."""
    val = await pool.fetchval(
        """
        SELECT 1 FROM referrals
        WHERE referrer_user_id = $1 AND referred_user_id = $2
        """,
        referrer_id,
        referred_id,
    )
    return val is not None


async def add_referral(
    pool: asyncpg.Pool, referrer_id: int, referred_id: int
) -> Optional[asyncpg.Record]:
    """
    Record a new referral. Returns the row or None if duplicate.
    Also increments the referrer's referral_count in the users table.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Insert referral record (skip if duplicate)
            row = await conn.fetchrow(
                """
                INSERT INTO referrals (referrer_user_id, referred_user_id)
                VALUES ($1, $2)
                ON CONFLICT (referrer_user_id, referred_user_id) DO NOTHING
                RETURNING *
                """,
                referrer_id,
                referred_id,
            )
            if row is None:
                return None  # Already existed

            # Increment referrer's count
            await conn.execute(
                """
                UPDATE users
                SET referral_count = referral_count + 1,
                    last_updated = NOW()
                WHERE user_id = $1
                """,
                referrer_id,
            )
            return row


async def get_referral_count(pool: asyncpg.Pool, user_id: int) -> int:
    """Count how many people this user has referred (from referrals table)."""
    val = await pool.fetchval(
        "SELECT COUNT(*) FROM referrals WHERE referrer_user_id = $1",
        user_id,
    )
    return val or 0
