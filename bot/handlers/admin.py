"""Admin panel — interactive menu accessible only to admins.

Entry point: /admin (or /panel)
Navigation is entirely callback-driven via inline keyboards.
Text input for settings changes uses FSM states.
"""

from __future__ import annotations

import logging

from aiogram import Bot, Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.db.pool import get_pool
from bot.db import config_repo, user_repo
from bot.keyboards.inline import (
    admin_main_menu,
    admin_settings_menu,
    admin_users_menu,
    admin_back_main,
    admin_cancel,
)
from bot.states import AdminInput
from bot.i18n import t

logger = logging.getLogger(__name__)

router = Router(name="admin")


# ═══════════════════════════════════════════════
# Guard
# ═══════════════════════════════════════════════

async def _is_admin(user_id: int) -> bool:
    pool = await get_pool()
    admin_ids = await config_repo.get_admin_ids(pool)
    return user_id in admin_ids


# ═══════════════════════════════════════════════
# /admin — open the admin panel
# ═══════════════════════════════════════════════

@router.message(Command("admin", "panel"))
async def cmd_admin(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return

    await state.clear()
    await message.answer(
        "<b>Admin Panel</b>\n\nPilih menu di bawah:",
        reply_markup=admin_main_menu(),
    )


# ═══════════════════════════════════════════════
# Callback: return to main menu
# ═══════════════════════════════════════════════

@router.callback_query(F.data == "adm_main")
async def cb_main_menu(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "<b>Admin Panel</b>\n\nPilih menu di bawah:",
        reply_markup=admin_main_menu(),
    )
    await callback.answer()


# ═══════════════════════════════════════════════
# Callback: close panel
# ═══════════════════════════════════════════════

@router.callback_query(F.data == "adm_close")
async def cb_close_panel(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await state.clear()
    await callback.message.delete()
    await callback.answer("Panel ditutup.")


# ═══════════════════════════════════════════════
# Callback: cancel any active FSM input
# ═══════════════════════════════════════════════

@router.callback_query(F.data == "adm_cancel")
async def cb_cancel(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "<b>Admin Panel</b>\n\nPilih menu di bawah:",
        reply_markup=admin_main_menu(),
    )
    await callback.answer("Dibatalkan.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STATISTICS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.callback_query(F.data == "adm_stats")
async def cb_stats(callback: types.CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    pool = await get_pool()
    stats = await user_repo.get_user_stats(pool)
    req = await config_repo.get_required_referrals(pool)
    aff = await config_repo.get_affiliate_link(pool) or "<i>not set</i>"
    expiry = await config_repo.get_invite_expiry(pool)

    total = stats["total_users"]
    verified = stats["verified_users"]
    joined = stats["joined_users"]
    rate = f"{verified / total * 100:.1f}" if total > 0 else "0"

    text = (
        "<b>Statistics</b>\n\n"
        f"Total users: <b>{total}</b>\n"
        f"Verified: <b>{verified}</b> ({rate}%)\n"
        f"Joined ZONA RATED: <b>{joined}</b>\n\n"
        "---- Current Config ----\n"
        f"Required referrals: <b>{req}</b>"
        f"{'  (auto-approve)' if req == 0 else ''}\n"
        f"Affiliate link: {aff}\n"
        f"Invite expiry: <b>{expiry}s</b>"
    )

    await callback.message.edit_text(text, reply_markup=admin_back_main())
    await callback.answer()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SETTINGS SUB-MENU
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.callback_query(F.data == "adm_settings")
async def cb_settings_menu(callback: types.CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    pool = await get_pool()
    req = await config_repo.get_required_referrals(pool)
    aff = await config_repo.get_affiliate_link(pool) or "-"
    expiry = await config_repo.get_invite_expiry(pool)
    welcome = await config_repo.get_welcome_message(pool)
    preview = welcome[:60] + ("..." if len(welcome) > 60 else "")

    text = (
        "<b>Settings</b>\n\n"
        f"Required Referrals: <b>{req}</b>\n"
        f"Affiliate Link: {aff}\n"
        f"Welcome: <i>{preview}</i>\n"
        f"Invite Expiry: <b>{expiry}s</b>\n\n"
        "Pilih setting yang ingin diubah:"
    )

    await callback.message.edit_text(text, reply_markup=admin_settings_menu())
    await callback.answer()


# ── Set Required Referrals ────────────────────

@router.callback_query(F.data == "adm_set_referrals")
async def cb_set_referrals_prompt(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await state.set_state(AdminInput.waiting_referrals)
    await callback.message.edit_text(
        "<b>Set Required Referrals</b>\n\n"
        "Kirim angka antara <b>0-10</b>.\n"
        "Set ke 0 = auto-approve (tanpa referral).",
        reply_markup=admin_cancel(),
    )
    await callback.answer()


@router.message(AdminInput.waiting_referrals)
async def on_referrals_input(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return

    try:
        val = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.reply("Kirim angka yang valid (0-10).")
        return

    if not 0 <= val <= 10:
        await message.reply("Angka harus antara 0 dan 10.")
        return

    pool = await get_pool()
    await config_repo.set_config(pool, "REQUIRED_REFERRALS", str(val))
    await state.clear()

    mode = "Auto-approve (tanpa referral)" if val == 0 else f"User perlu {val} referral"
    await message.answer(
        f"<b>Required Referrals</b> diperbarui ke <b>{val}</b>\n{mode}",
        reply_markup=admin_back_main(),
    )


# ── Set Affiliate Link ────────────────────────

@router.callback_query(F.data == "adm_set_affiliate")
async def cb_set_affiliate_prompt(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await state.set_state(AdminInput.waiting_affiliate)
    await callback.message.edit_text(
        "<b>Set Affiliate Link</b>\n\n"
        "Kirim URL baru (harus dimulai dengan http:// atau https://).",
        reply_markup=admin_cancel(),
    )
    await callback.answer()


@router.message(AdminInput.waiting_affiliate)
async def on_affiliate_input(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return

    url = (message.text or "").strip()
    if not url.startswith(("http://", "https://")):
        await message.reply("URL harus dimulai dengan http:// atau https://")
        return

    pool = await get_pool()
    await config_repo.set_config(pool, "AFFILIATE_LINK", url)
    await state.clear()

    await message.answer(
        f"<b>Affiliate Link</b> diperbarui!\n{url}",
        reply_markup=admin_back_main(),
    )


# ── Set Welcome Message ───────────────────────

@router.callback_query(F.data == "adm_set_welcome")
async def cb_set_welcome_prompt(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await state.set_state(AdminInput.waiting_welcome)
    await callback.message.edit_text(
        "<b>Set Welcome Message</b>\n\n"
        "Kirim pesan selamat datang baru.\n"
        "HTML formatting didukung (bold, italic, link, dll).",
        reply_markup=admin_cancel(),
    )
    await callback.answer()


@router.message(AdminInput.waiting_welcome)
async def on_welcome_input(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return

    text = (message.text or "").strip()
    if not text:
        await message.reply("Pesan tidak boleh kosong.")
        return

    pool = await get_pool()
    await config_repo.set_config(pool, "WELCOME_MESSAGE", text)
    await state.clear()

    await message.answer(
        f"<b>Welcome Message</b> diperbarui!\n\nPreview:\n{text}",
        reply_markup=admin_back_main(),
    )


# ── Set Invite Expiry ─────────────────────────

@router.callback_query(F.data == "adm_set_expiry")
async def cb_set_expiry_prompt(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await state.set_state(AdminInput.waiting_expiry)
    await callback.message.edit_text(
        "<b>Set Invite Expiry</b>\n\n"
        "Kirim durasi dalam detik (60-3600).\n"
        "Default: 300 (5 menit).",
        reply_markup=admin_cancel(),
    )
    await callback.answer()


@router.message(AdminInput.waiting_expiry)
async def on_expiry_input(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return

    try:
        val = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.reply("Kirim angka yang valid (60-3600).")
        return

    if not 60 <= val <= 3600:
        await message.reply("Angka harus antara 60 dan 3600 detik.")
        return

    pool = await get_pool()
    await config_repo.set_config(pool, "INVITE_EXPIRY_SECONDS", str(val))
    await state.clear()

    await message.answer(
        f"<b>Invite Expiry</b> diperbarui ke <b>{val} detik</b> "
        f"({val // 60} menit {val % 60} detik)",
        reply_markup=admin_back_main(),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USER MANAGEMENT SUB-MENU
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.callback_query(F.data == "adm_users")
async def cb_users_menu(callback: types.CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await callback.message.edit_text(
        "<b>User Management</b>\n\nPilih aksi:",
        reply_markup=admin_users_menu(),
    )
    await callback.answer()


# ── Approve User ──────────────────────────────

@router.callback_query(F.data == "adm_approve")
async def cb_approve_prompt(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await state.set_state(AdminInput.waiting_approve_id)
    await callback.message.edit_text(
        "<b>Approve User</b>\n\n"
        "Kirim Telegram User ID yang ingin di-approve.\n"
        "User akan langsung bisa join ZONA RATED.",
        reply_markup=admin_cancel(),
    )
    await callback.answer()


@router.message(AdminInput.waiting_approve_id)
async def on_approve_input(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return

    try:
        target_id = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.reply("User ID tidak valid. Kirim angka.")
        return

    pool = await get_pool()
    user = await user_repo.get_user(pool, target_id)
    if user is None:
        await message.reply(
            "User tidak ditemukan di database.\n"
            "Pastikan user sudah pernah /start ke bot.",
        )
        return

    await user_repo.set_verification_complete(pool, target_id)
    await state.clear()

    name = user["first_name"] or user["username"] or str(target_id)
    await message.answer(
        f"User <b>{name}</b> (ID: <code>{target_id}</code>) berhasil di-approve!",
        reply_markup=admin_back_main(),
    )

    # Try to notify the approved user
    try:
        target_lang = await user_repo.get_language(pool, target_id) or "id"
        bot: Bot = message.bot
        await bot.send_message(
            target_id,
            t(target_lang, "admin_approved_you"),
        )
    except Exception:
        logger.warning("Could not notify user %s about approval", target_id)


# ── Lookup User ───────────────────────────────

@router.callback_query(F.data == "adm_lookup")
async def cb_lookup_prompt(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await state.set_state(AdminInput.waiting_lookup_id)
    await callback.message.edit_text(
        "<b>Lookup User</b>\n\n"
        "Kirim Telegram User ID untuk melihat detail.",
        reply_markup=admin_cancel(),
    )
    await callback.answer()


@router.message(AdminInput.waiting_lookup_id)
async def on_lookup_input(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return

    try:
        target_id = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.reply("User ID tidak valid. Kirim angka.")
        return

    pool = await get_pool()
    user = await user_repo.get_user(pool, target_id)
    if user is None:
        await message.reply("User tidak ditemukan di database.")
        return

    await state.clear()

    ref_required = await config_repo.get_required_referrals(pool)
    refs = user["referral_count"]

    name = user["first_name"] or "-"
    uname = f"@{user['username']}" if user["username"] else "-"
    referred_by = user["referred_by"] or "-"
    user_lang = user["language"] or "-"

    text = (
        f"<b>User Detail</b>\n\n"
        f"ID: <code>{target_id}</code>\n"
        f"Name: {name}\n"
        f"Username: {uname}\n"
        f"Language: {user_lang}\n"
        f"Referred by: <code>{referred_by}</code>\n"
        f"Referrals: <b>{refs}/{ref_required}</b>\n\n"
        f"Verified: {'Ya' if user['verification_complete'] else 'Tidak'}\n"
        f"Ready to join: {'Ya' if user['ready_to_join'] else 'Tidak'}\n"
        f"Joined SG: {'Ya' if user['joined_supergroup'] else 'Tidak'}\n"
        f"Approved: {'Ya' if user['approved'] else 'Tidak'}\n\n"
        f"Registered: {user['created_at'].strftime('%Y-%m-%d %H:%M')}\n"
        f"Last update: {user['last_updated'].strftime('%Y-%m-%d %H:%M')}"
    )

    await message.answer(text, reply_markup=admin_back_main())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BROADCAST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.callback_query(F.data == "adm_broadcast")
async def cb_broadcast_prompt(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await state.set_state(AdminInput.waiting_broadcast)
    await callback.message.edit_text(
        "<b>Broadcast Message</b>\n\n"
        "Kirim pesan yang ingin dikirim ke <b>semua user</b>.\n"
        "HTML formatting didukung.\n\n"
        "Pesan akan dikirim satu per satu.",
        reply_markup=admin_cancel(),
    )
    await callback.answer()


@router.message(AdminInput.waiting_broadcast)
async def on_broadcast_input(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return

    text = (message.text or "").strip()
    if not text:
        await message.reply("Pesan tidak boleh kosong.")
        return

    await state.clear()

    pool = await get_pool()
    rows = await pool.fetch("SELECT user_id FROM users")

    bot: Bot = message.bot
    sent = 0
    failed = 0

    status_msg = await message.answer(
        f"Mengirim broadcast ke {len(rows)} user..."
    )

    for row in rows:
        try:
            await bot.send_message(row["user_id"], text)
            sent += 1
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"<b>Broadcast selesai!</b>\n\n"
        f"Terkirim: {sent}\n"
        f"Gagal: {failed}\n"
        f"Total: {len(rows)}",
        reply_markup=admin_back_main(),
    )
