"""/start command — language selection + onboarding + referral handling."""

from __future__ import annotations

import logging

from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from bot.config import settings
from bot.db.pool import get_pool
from bot.db import config_repo, user_repo, referral_repo
from bot.keyboards.inline import (
    language_keyboard,
    welcome_keyboard,
    welcome_auto_keyboard,
    gabung_grup_keyboard,
)
from bot.states import UserOnboarding
from bot.i18n import t

logger = logging.getLogger(__name__)

router = Router(name="start")

BOT_USERNAME = "zonarated_bot"


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

    # ── Parse referral parameter ──────────────────────
    referrer_id: int | None = None
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].removeprefix("ref_"))
        except ValueError:
            referrer_id = None

        # Don't let users refer themselves
        if referrer_id == user_id:
            referrer_id = None

    # ── Create / update user in DB ────────────────────
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
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
