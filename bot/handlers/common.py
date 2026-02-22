"""Common user commands: /help, /status, /mylink, and fallback."""

from __future__ import annotations

from aiogram import Router, types, F
from aiogram.filters import Command

from bot.db.pool import get_pool
from bot.db import config_repo, user_repo
from bot.i18n import t
from bot.keyboards.inline import fallback_keyboard, start_keyboard

router = Router(name="common")


# ──────────────────────────────────────────────
# /help
# ──────────────────────────────────────────────

@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    """Show available commands."""
    pool = await get_pool()
    lang = await user_repo.get_language(pool, message.from_user.id) or "id"
    await message.reply(t(lang, "help_text"))


# ──────────────────────────────────────────────
# /status
# ──────────────────────────────────────────────

@router.message(Command("status"))
async def cmd_status(message: types.Message) -> None:
    """Show user's verification status and referral progress."""
    pool = await get_pool()
    user_id = message.from_user.id

    user = await user_repo.get_user(pool, user_id)
    if user is None:
        lang = "id"
        await message.reply(t(lang, "not_registered"))
        return

    lang = user["language"] or "id"
    ref_count = user["referral_count"]
    ref_required = await config_repo.get_required_referrals(pool)
    verified = user["verification_complete"]

    # Live check: is user actually in the supergroup?
    from bot.config import settings
    try:
        member = await message.bot.get_chat_member(
            chat_id=settings.supergroup_id, user_id=user_id)
        in_group = member.status in ("member", "administrator", "creator")
    except Exception:
        in_group = user["joined_supergroup"]  # fallback to DB

    # Sync DB if user joined but DB not updated yet
    if in_group and not user["joined_supergroup"]:
        await user_repo.set_joined_supergroup(pool, user_id)

    sg_status = t(lang, "yes") if in_group else t(lang, "no")
    ver_status = t(lang, "complete") if verified else t(lang, "incomplete")

    text = t(lang, "status_text",
             count=ref_count,
             required=ref_required,
             sg_status=sg_status,
             ver_status=ver_status,
             ref_link=user["referral_link"])

    await message.reply(text)


# ──────────────────────────────────────────────
# /mylink
# ──────────────────────────────────────────────

@router.message(Command("mylink"))
async def cmd_mylink(message: types.Message) -> None:
    """Show user's referral link."""
    pool = await get_pool()
    user_id = message.from_user.id

    user = await user_repo.get_user(pool, user_id)
    if user is None:
        lang = "id"
        await message.reply(t(lang, "not_registered"))
        return

    lang = user["language"] or "id"
    ref_count = user["referral_count"]
    ref_required = await config_repo.get_required_referrals(pool)

    await message.reply(
        t(lang, "mylink_text",
          ref_link=user["referral_link"],
          count=ref_count,
          required=ref_required),
    )


# ──────────────────────────────────────────────
# Fallback callbacks: fb_status, fb_help
# ──────────────────────────────────────────────

@router.callback_query(F.data == "fb_status")
async def cb_fb_status(callback: types.CallbackQuery) -> None:
    """Quick status via fallback button."""
    pool = await get_pool()
    user_id = callback.from_user.id

    user = await user_repo.get_user(pool, user_id)
    if user is None:
        await callback.answer(t("id", "not_registered"), show_alert=True)
        return

    lang = user["language"] or "id"
    ref_count = user["referral_count"]
    ref_required = await config_repo.get_required_referrals(pool)
    joined_sg = user["joined_supergroup"]
    verified = user["verification_complete"]

    ref_status = "OK" if ref_count >= ref_required else "X"
    sg_status = t(lang, "yes") if joined_sg else t(lang, "no")
    ver_status = t(lang, "complete") if verified else t(lang, "incomplete")

    text = t(lang, "status_text",
             count=ref_count,
             required=ref_required,
             ref_status=ref_status,
             sg_status=sg_status,
             ver_status=ver_status,
             ref_link=user["referral_link"])

    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "fb_help")
async def cb_fb_help(callback: types.CallbackQuery) -> None:
    """Quick help via fallback button."""
    pool = await get_pool()
    lang = await user_repo.get_language(pool, callback.from_user.id) or "id"
    await callback.message.answer(t(lang, "help_text"))
    await callback.answer()


# ──────────────────────────────────────────────
# Fallback: any unrecognized message (private chat only)
# ──────────────────────────────────────────────

@router.message(F.chat.type == "private")
async def fallback(message: types.Message) -> None:
    """Catch-all for messages not matched by other handlers."""
    pool = await get_pool()
    user_id = message.from_user.id

    user = await user_repo.get_user(pool, user_id)
    if user is None:
        await message.reply(
            t("id", "fallback_new"),
            reply_markup=start_keyboard(),
        )
        return

    lang = user["language"] or "id"
    ref_count = user["referral_count"]
    ref_required = await config_repo.get_required_referrals(pool)
    share_text = t(lang, "share_text", ref_link=user["referral_link"])

    await message.reply(
        t(lang, "fallback_registered",
          ref_link=user["referral_link"],
          count=ref_count,
          required=ref_required),
        reply_markup=fallback_keyboard(
            ref_link=user["referral_link"],
            share_text=share_text,
            btn_share=t(lang, "btn_share"),
            btn_status="Status",
            btn_help="Help",
        ),
    )
