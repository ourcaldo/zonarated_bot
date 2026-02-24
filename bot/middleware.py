"""Maintenance-mode middleware — blocks non-admin users when enabled.

Registered as an *outer* middleware on the Dispatcher so it intercepts
every update type (messages, callbacks, inline queries, etc.).

The mode is controlled by three config keys:
    MAINTENANCE_MODE   – "true" / "false"
    MAINTENANCE_START  – optional ISO-8601 datetime (start of window)
    MAINTENANCE_END    – optional ISO-8601 datetime (end of window)

When the mode is active and the user is not an admin, the bot replies
with a maintenance notice and drops the update.
"""

from __future__ import annotations

import logging
import time as _time
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, types

from bot.db.pool import get_pool
from bot.db import config_repo, user_repo

logger = logging.getLogger(__name__)

# In-memory cache so we don't query the DB on every single update.
_cache: dict[str, Any] = {"ts": 0, "enabled": False, "start": None, "end": None}
_CACHE_TTL = 30  # seconds


def invalidate_maintenance_cache() -> None:
    """Force the next middleware call to re-read the DB.

    Call this from admin handlers right after changing maintenance config.
    """
    _cache["ts"] = 0


async def _refresh_cache() -> None:
    now = _time.monotonic()
    if now - _cache["ts"] < _CACHE_TTL:
        return

    pool = await get_pool()
    raw = await config_repo.get_config(pool, "MAINTENANCE_MODE")
    enabled = (raw or "").strip().lower() in ("true", "1", "yes")

    start_str = await config_repo.get_config(pool, "MAINTENANCE_START")
    end_str = await config_repo.get_config(pool, "MAINTENANCE_END")

    start_dt = None
    end_dt = None
    if start_str:
        try:
            start_dt = datetime.fromisoformat(start_str)
        except ValueError:
            pass
    if end_str:
        try:
            end_dt = datetime.fromisoformat(end_str)
        except ValueError:
            pass

    _cache.update(ts=now, enabled=enabled, start=start_dt, end=end_dt)


def _is_within_window() -> bool:
    """Return True if current time is within the optional maintenance window."""
    start = _cache["start"]
    end = _cache["end"]
    if start is None and end is None:
        return True  # no window set — always active
    now = datetime.now(timezone.utc)
    if start and now < start.astimezone(timezone.utc):
        return False
    if end and now > end.astimezone(timezone.utc):
        return False
    return True


def is_maintenance_active() -> bool:
    """Quick check using cached values (does NOT refresh)."""
    return _cache["enabled"] and _is_within_window()


class MaintenanceMiddleware(BaseMiddleware):
    """Outer middleware that blocks non-admin users during maintenance."""

    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        await _refresh_cache()

        if not is_maintenance_active():
            return await handler(event, data)

        # Determine user_id from the event
        user_id: int | None = None
        if isinstance(event, types.Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, types.CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, types.ChatJoinRequest):
            user_id = event.from_user.id if event.from_user else None

        if user_id is None:
            return await handler(event, data)

        # Admins pass through
        pool = await get_pool()
        admin_ids = await config_repo.get_admin_ids(pool)
        if user_id in admin_ids:
            return await handler(event, data)

        # Block the user with a maintenance message
        lang = await user_repo.get_language(pool, user_id) or "id"
        end_dt = _cache.get("end")
        if end_dt:
            end_str = end_dt.strftime("%Y-%m-%d %H:%M UTC")
            if lang == "en":
                text = (
                    "The bot is currently under maintenance.\n"
                    f"Estimated completion: {end_str}"
                )
            else:
                text = (
                    "Bot sedang dalam pemeliharaan.\n"
                    f"Estimasi selesai: {end_str}"
                )
        else:
            if lang == "en":
                text = "The bot is currently under maintenance. Please try again later."
            else:
                text = "Bot sedang dalam pemeliharaan. Silakan coba lagi nanti."

        bot = data.get("bot")
        if bot and isinstance(event, types.Message) and event.chat:
            try:
                await bot.send_message(event.chat.id, text)
            except Exception:
                pass
        elif bot and isinstance(event, types.CallbackQuery):
            try:
                await event.answer(text[:200], show_alert=True)
            except Exception:
                pass

        # Drop the update — do NOT call handler
        return None
