"""Repository for the `config` table — dynamic key-value settings."""

from __future__ import annotations

from typing import Optional

import asyncpg


async def get_config(pool: asyncpg.Pool, key: str) -> Optional[str]:
    """Get a config value by key. Returns None if not found."""
    return await pool.fetchval(
        "SELECT value FROM config WHERE key = $1", key
    )


async def get_config_int(pool: asyncpg.Pool, key: str, default: int = 0) -> int:
    """Get a config value as integer, with a fallback default."""
    val = await get_config(pool, key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


async def set_config(pool: asyncpg.Pool, key: str, value: str) -> None:
    """Insert or update a config value."""
    await pool.execute(
        """
        INSERT INTO config (key, value, updated_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (key) DO UPDATE
            SET value = EXCLUDED.value,
                updated_at = NOW()
        """,
        key,
        value,
    )


async def get_required_referrals(pool: asyncpg.Pool) -> int:
    """Shortcut: get REQUIRED_REFERRALS (default 0)."""
    return await get_config_int(pool, "REQUIRED_REFERRALS", default=0)


async def get_invite_expiry(pool: asyncpg.Pool) -> int:
    """Shortcut: get INVITE_EXPIRY_SECONDS (default 300)."""
    return await get_config_int(pool, "INVITE_EXPIRY_SECONDS", default=300)


async def get_admin_ids(pool: asyncpg.Pool) -> list[int]:
    """Shortcut: get ADMIN_IDS as a list of ints."""
    raw = await get_config(pool, "ADMIN_IDS")
    if not raw:
        return []
    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


async def get_affiliate_link(pool: asyncpg.Pool) -> str:
    """Shortcut: get AFFILIATE_LINK (default empty)."""
    return await get_config(pool, "AFFILIATE_LINK") or ""


async def get_welcome_message(pool: asyncpg.Pool) -> str:
    """Shortcut: get WELCOME_MESSAGE."""
    return (
        await get_config(pool, "WELCOME_MESSAGE")
        or "Selamat datang di ZONA RATED!"
    )


async def get_shrinkme_api_key(pool: asyncpg.Pool) -> str:
    """Shortcut: get SHRINKME_API_KEY (empty string if not set)."""
    return await get_config(pool, "SHRINKME_API_KEY") or ""


async def get_shrinkme_enabled(pool: asyncpg.Pool) -> bool:
    """Shortcut: check if ShrinkMe URL shortening is enabled (default True)."""
    val = await get_config(pool, "SHRINKME_ENABLED")
    if val is None:
        return True
    return val.strip().lower() in ("true", "1", "yes")


async def get_redirect_base_url(pool: asyncpg.Pool) -> str:
    """Shortcut: get REDIRECT_BASE_URL (empty string if not set)."""
    return await get_config(pool, "REDIRECT_BASE_URL") or ""


async def get_all_config(pool: asyncpg.Pool) -> list:
    """Get all config rows ordered by key."""
    return await pool.fetch("SELECT key, value, description FROM config ORDER BY key")
