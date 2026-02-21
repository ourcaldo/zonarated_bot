"""Handle supergroup join requests — Method 3 double verification."""

from __future__ import annotations

import logging

from aiogram import Router, types

from bot.config import settings
from bot.db.pool import get_pool
from bot.db import user_repo
from bot.i18n import t

logger = logging.getLogger(__name__)

router = Router(name="join_request")


@router.chat_join_request()
async def handle_join_request(event: types.ChatJoinRequest) -> None:
    """
    Triggered when a user clicks the invite link and the supergroup
    has 'Approve new members' enabled.

    This is the SECOND layer of verification (Method 3).
    Even with a valid link, we re-check everything.
    """
    user_id = event.from_user.id
    chat_id = event.chat.id

    # Only handle our supergroup
    if chat_id != settings.supergroup_id:
        return

    pool = await get_pool()
    lang = await user_repo.get_language(pool, user_id) or "id"

    # ── Re-verify user ────────────────────────────────
    verified = await user_repo.is_verified(pool, user_id)
    ready = await user_repo.is_ready_to_join(pool, user_id)
    approved = await user_repo.is_approved(pool, user_id)

    if verified and ready and approved:
        # ═══ ALL CHECKS PASSED ════════════════════
        try:
            await event.approve()

            # Update DB flags
            await user_repo.set_joined_supergroup(pool, user_id)

            # Send welcome PM
            await event.bot.send_message(
                user_id,
                t(lang, "join_approved"),
            )
            logger.info("Approved join request for user %s", user_id)

        except Exception as e:
            logger.error("Error approving join for user %s: %s", user_id, e)

    else:
        # ═══ CHECKS FAILED ════════════════════════
        try:
            await event.decline()

            reasons: list[str] = []
            if not verified:
                reasons.append(t(lang, "reason_not_verified"))
            if not ready:
                reasons.append(t(lang, "reason_link_expired"))
            if not approved:
                reasons.append(t(lang, "reason_not_approved"))

            reason_text = "\n".join(reasons)

            await event.bot.send_message(
                user_id,
                t(lang, "join_declined", reasons=reason_text),
            )
            logger.info("Declined join request for user %s (verified=%s, ready=%s, approved=%s)",
                        user_id, verified, ready, approved)

        except Exception as e:
            logger.error("Error declining join for user %s: %s", user_id, e)
