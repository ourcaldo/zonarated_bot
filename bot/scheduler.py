"""Background scheduler — periodic tasks that run alongside polling.

Currently runs one task:
  - check_newly_qualified: every 60s, scans for users who now meet the
    referral requirement but haven't been notified yet, and sends them
    a congratulations message with a join button.
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from bot.db.pool import get_pool
from bot.db import config_repo, user_repo
from bot.keyboards.inline import gabung_grup_keyboard
from bot.i18n import t

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 60  # seconds


async def _check_newly_qualified(bot: Bot) -> None:
    """Find users who meet referral requirements but are not yet verified."""
    pool = await get_pool()
    required = await config_repo.get_required_referrals(pool)

    if required == 0:
        # Auto-approve mode — nothing to scan
        return

    # Users who have enough referrals but haven't been marked verified
    rows = await pool.fetch(
        """
        SELECT user_id, referral_count, language
        FROM users
        WHERE referral_count >= $1
          AND verification_complete = FALSE
        """,
        required,
    )

    if not rows:
        return

    logger.info("Scheduler: found %d newly qualified user(s)", len(rows))

    for row in rows:
        uid = row["user_id"]
        count = row["referral_count"]
        lang = row["language"] or "id"

        # Mark verified so we don't notify again
        await user_repo.set_verification_complete(pool, uid)

        try:
            await bot.send_message(
                uid,
                t(lang, "referral_complete", count=count, required=required),
                reply_markup=gabung_grup_keyboard(t(lang, "btn_join")),
            )
            logger.info("Scheduler: notified user %s (refs=%d)", uid, count)
        except Exception:
            logger.warning("Scheduler: could not notify user %s", uid)


async def start_scheduler(bot: Bot) -> None:
    """Run periodic tasks forever. Call this as a background asyncio task."""
    logger.info("Scheduler started (interval=%ds)", CHECK_INTERVAL)
    while True:
        try:
            await _check_newly_qualified(bot)
        except Exception:
            logger.exception("Scheduler error in check_newly_qualified")
        await asyncio.sleep(CHECK_INTERVAL)
