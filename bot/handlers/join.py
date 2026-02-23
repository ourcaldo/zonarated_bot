"""Check requirements callback — verification check + invite link generation."""

from __future__ import annotations

import logging
import time

from aiogram import Router, types, Bot
from aiogram.exceptions import TelegramBadRequest

from bot.config import settings
from bot.db.pool import get_pool
from bot.db import config_repo, user_repo
from bot.keyboards.inline import check_again_keyboard, join_supergroup_keyboard
from bot.i18n import t

logger = logging.getLogger(__name__)

router = Router(name="join")


@router.callback_query(lambda c: c.data == "check_req")
async def handle_check_req(callback: types.CallbackQuery, bot: Bot) -> None:
    """User clicked 'Cek Persyaratan' / 'Check Requirements'."""
    pool = await get_pool()
    user_id = callback.from_user.id

    # ── Fetch user & verification data ────────────────
    user = await user_repo.get_user(pool, user_id)
    if user is None:
        lang = "id"
        await callback.answer(t(lang, "not_registered"), show_alert=True)
        return

    lang = user["language"] or "id"
    ref_count = user["referral_count"]
    ref_required = await config_repo.get_required_referrals(pool)
    is_complete = ref_count >= ref_required

    if is_complete:
        # ═══════════════════════════════════════════════
        # VERIFIED — generate secure one-time invite
        # ═══════════════════════════════════════════════
        await user_repo.set_verification_complete(pool, user_id)
        await user_repo.set_ready_to_join(pool, user_id, True)

        invite_expiry = await config_repo.get_invite_expiry(pool)

        try:
            invite = await bot.create_chat_invite_link(
                chat_id=settings.supergroup_id,
                member_limit=1,
                expire_date=int(time.time()) + invite_expiry,
            )

            text = t(lang, "verified_ready",
                     count=ref_count,
                     required=ref_required,
                     expiry_min=invite_expiry // 60)

            try:
                await callback.message.edit_text(
                    text,
                    reply_markup=join_supergroup_keyboard(
                        invite.invite_link,
                        t(lang, "btn_join_supergroup")),
                )
            except TelegramBadRequest:
                pass  # message content unchanged — ignore

            await callback.answer(t(lang, "invite_created"))

        except TelegramBadRequest:
            pass  # already handled above
        except Exception as e:
            logger.error("Failed to create invite link: %s", e)
            await callback.answer(t(lang, "invite_failed"), show_alert=True)

    else:
        # ═══════════════════════════════════════════════
        # NOT VERIFIED — show what's missing
        # ═══════════════════════════════════════════════
        ref_link = user["referral_link"]
        needed = max(0, ref_required - ref_count)

        if ref_required > 0:
            status_msg = t(lang, "not_verified",
                          count=ref_count,
                          required=ref_required,
                          needed=needed,
                          ref_link=ref_link)
        else:
            status_msg = t(lang, "not_verified_auto")

        share_text = t(lang, "share_text", ref_link=ref_link)

        try:
            await callback.message.edit_text(
                status_msg,
                reply_markup=check_again_keyboard(
                    ref_link,
                    share_text,
                    t(lang, "btn_share_again"),
                    t(lang, "btn_check_again")),
            )
        except TelegramBadRequest:
            pass  # message content unchanged — ignore

        await callback.answer(t(lang, "check_requirements_first"), show_alert=True)
