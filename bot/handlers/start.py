"""/start command — language selection + onboarding + referral handling."""

from __future__ import annotations

import logging

from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from bot.config import settings
from bot.db.pool import get_pool
from bot.db import config_repo, user_repo, referral_repo, video_repo
from bot.keyboards.inline import (
    language_keyboard,
    welcome_keyboard,
    welcome_auto_keyboard,
    gabung_grup_keyboard,
    download_session_button,
)
from bot.states import UserOnboarding
from bot.i18n import t
import bot.config as bot_config

logger = logging.getLogger(__name__)

router = Router(name="start")


# ──────────────────────────────────────────────
# Download deep link handler
# ──────────────────────────────────────────────

async def _handle_download_deep_link(
    message: types.Message, pool, user_id: int, deep_link: str
) -> None:
    """Handle /start dl_VIDEOID — download flow via deep link."""
    try:
        video_id = int(deep_link.removeprefix("dl_"))
    except ValueError:
        await message.answer("Video tidak valid.")
        return

    bot = message.bot

    # Check if user is registered
    user = await user_repo.get_user(pool, user_id)
    lang = (user["language"] if user else None) or "id"

    if not user:
        await message.answer(t(lang, "dl_not_registered"))
        return

    # Check if user is verified
    if not user["verification_complete"]:
        await message.answer(t(lang, "dl_not_verified"))
        return

    # Get video
    video = await video_repo.get_video(pool, video_id)
    if not video:
        await message.answer("Video tidak ditemukan.")
        return

    # Increment views
    await video_repo.increment_views(pool, video_id)

    # Get affiliate link (per-video override or global)
    affiliate = video["affiliate_link"]
    if not affiliate:
        affiliate = await config_repo.get_affiliate_link(pool)

    if affiliate:
        # Create a download session
        session_id = await video_repo.create_download_session(pool, user_id, video_id)

        # Build redirect URL using REDIRECT_BASE_URL
        base_url = await config_repo.get_redirect_base_url(pool)
        if base_url:
            redirect_url = f"{base_url.rstrip('/')}/{session_id}"
        else:
            # Fallback: direct affiliate link if no redirect base configured
            redirect_url = affiliate

        # Send affiliate gate with redirect link
        await message.answer(
            t(lang, "dl_affiliate_prompt"),
            reply_markup=download_session_button(redirect_url),
        )
    else:
        # No affiliate link — deliver directly
        from bot.handlers.video import _deliver_video
        try:
            await _deliver_video(bot, user_id, video, lang)
            session_id = await video_repo.create_download_session(pool, user_id, video_id)
            await video_repo.mark_affiliate_visited(pool, session_id)
            await video_repo.mark_video_sent(pool, session_id)
            await video_repo.increment_downloads(pool, video_id)
            await video_repo.log_download(pool, user_id, video_id, session_id, False)
        except Exception as e:
            logger.warning("Could not deliver video to user %s: %s", user_id, e)
            await message.answer(t(lang, "dl_error"))


async def _send_welcome(message_or_callback, user_id: int, lang: str, pool) -> None:
    """Build and send the welcome message with appropriate buttons."""
    user = await user_repo.get_user(pool, user_id)
    ref_link = user["referral_link"]
    required = await config_repo.get_required_referrals(pool)
    welcome_msg = await config_repo.get_welcome_message(pool)

    if required == 0:
        text = t(lang, "welcome_auto", welcome_msg=welcome_msg)
        kb = welcome_auto_keyboard(t(lang, "btn_join"))
    else:
        text = t(lang, "welcome", welcome_msg=welcome_msg, required=required, ref_link=ref_link)
        share_text = t(lang, "share_text", ref_link=ref_link)
        kb = welcome_keyboard(ref_link, share_text, t(lang, "btn_share"), t(lang, "btn_check"))

    # Determine send method
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=kb)
    else:
        await message_or_callback.answer(text, reply_markup=kb)


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    """Handle /start and /start ref_USERID."""
    pool = await get_pool()
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    # ── Parse deep link parameter ──────────────────────
    args = message.text.split(maxsplit=1)
    deep_link = args[1] if len(args) > 1 else None

    # ── Download deep link: /start dl_VIDEOID ─────────
    if deep_link and deep_link.startswith("dl_"):
        await _handle_download_deep_link(message, pool, user_id, deep_link)
        return

    # ── Parse referral parameter ──────────────────────
    referrer_id: int | None = None
    if deep_link and deep_link.startswith("ref_"):
        try:
            referrer_id = int(deep_link.removeprefix("ref_"))
        except ValueError:
            referrer_id = None

        # Don't let users refer themselves
        if referrer_id == user_id:
            referrer_id = None

    # ── Create / update user in DB ────────────────────
    ref_link = f"https://t.me/{bot_config.bot_username}?start=ref_{user_id}"
    await user_repo.create_user(
        pool,
        user_id=user_id,
        username=username,
        first_name=first_name,
        referral_link=ref_link,
        referred_by=referrer_id,
    )

    # ── Process referral credit ───────────────────────
    if referrer_id is not None:
        referrer = await user_repo.get_user(pool, referrer_id)
        if referrer is not None:
            result = await referral_repo.add_referral(pool, referrer_id, user_id)
            if result is not None:
                new_count = await user_repo.get_referral_count(pool, referrer_id)
                required = await config_repo.get_required_referrals(pool)
                referrer_lang = await user_repo.get_language(pool, referrer_id) or "id"

                try:
                    await message.bot.send_message(
                        referrer_id,
                        t(referrer_lang, "referral_credited",
                          count=new_count, required=required),
                    )
                except Exception:
                    logger.debug("Could not notify referrer %s", referrer_id)

                # If referrer just completed the requirement
                if required > 0 and new_count >= required:
                    try:
                        await message.bot.send_message(
                            referrer_id,
                            t(referrer_lang, "referral_complete",
                              count=new_count, required=required),
                            reply_markup=gabung_grup_keyboard(
                                t(referrer_lang, "btn_join")),
                        )
                    except Exception:
                        logger.debug("Could not send completion msg to referrer %s", referrer_id)

    # ── Check if user already has language set ────────
    lang = await user_repo.get_language(pool, user_id)
    if lang:
        # Returning user — skip language selection, show welcome directly
        await _send_welcome(message, user_id, lang, pool)
    else:
        # New user — ask for language
        await state.set_state(UserOnboarding.choosing_language)
        await state.update_data(user_id=user_id)
        await message.answer(
            t("id", "choose_language"),
            reply_markup=language_keyboard(),
        )


# ──────────────────────────────────────────────
# Language selection callback
# ──────────────────────────────────────────────

@router.callback_query(F.data.in_({"lang_id", "lang_en"}))
async def on_language_chosen(callback: types.CallbackQuery, state: FSMContext) -> None:
    """User picked a language."""
    lang = callback.data.removeprefix("lang_")  # 'id' or 'en'
    user_id = callback.from_user.id

    pool = await get_pool()
    await user_repo.set_language(pool, user_id, lang)
    await state.clear()

    await _send_welcome(callback, user_id, lang, pool)
    await callback.answer()
