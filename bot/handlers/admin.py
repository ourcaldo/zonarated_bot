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
from bot.db import config_repo, user_repo, topic_repo, video_repo
import time

from bot.config import settings
from bot.keyboards.inline import (
    admin_main_menu,
    admin_settings_menu,
    admin_users_menu,
    admin_back_main,
    admin_cancel,
    admin_category_menu,
    category_remove_keyboard,
    category_set_all_keyboard,
    join_supergroup_keyboard,
)
from bot.states import AdminInput, AdminCategory
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
    config_rows = await config_repo.get_all_config(pool)

    text = "<b>Settings</b>\n\nSemua pengaturan dari database:\n\n"
    for cfg in config_rows:
        key = cfg["key"]
        val = cfg["value"] or "<i>empty</i>"
        preview = val[:50] + ("..." if len(val) > 50 else "")
        text += f"<code>{key}</code>\n  {preview}\n\n"
    text += "Pilih setting yang ingin diubah:"

    await callback.message.edit_text(
        text, reply_markup=admin_settings_menu(config_rows)
    )
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


# ── Maintenance Mode Toggle (special) ─────────

from bot.keyboards.inline import maintenance_toggle_keyboard
from bot.middleware import invalidate_maintenance_cache

@router.callback_query(F.data == "adm_toggle_MAINTENANCE_MODE")
async def cb_maintenance_toggle(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Special handler for maintenance mode — offers time-window option."""
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    pool = await get_pool()
    current = await config_repo.get_config(pool, "MAINTENANCE_MODE") or "false"
    is_on = current.strip().lower() in ("true", "1", "yes")

    if is_on:
        # Turn OFF
        await config_repo.set_config(pool, "MAINTENANCE_MODE", "false")
        await config_repo.set_config(pool, "MAINTENANCE_START", "")
        await config_repo.set_config(pool, "MAINTENANCE_END", "")
        invalidate_maintenance_cache()
        await callback.answer("Maintenance mode OFF", show_alert=False)
        config_rows = await config_repo.get_all_config(pool)
        await callback.message.edit_text(
            "<b>Settings</b>\n\nPilih pengaturan yang ingin diubah:",
            reply_markup=admin_settings_menu(config_rows),
        )
    else:
        # Ask: enable with or without time window?
        await callback.message.edit_text(
            "<b>Maintenance Mode</b>\n\n"
            "Enable maintenance mode?\n"
            "You can set a time window or enable it immediately.",
            reply_markup=maintenance_toggle_keyboard(),
        )
        await callback.answer()


@router.callback_query(F.data == "maint_now")
async def cb_maint_enable_now(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Enable maintenance immediately without time window."""
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    pool = await get_pool()
    await config_repo.set_config(pool, "MAINTENANCE_MODE", "true")
    await config_repo.set_config(pool, "MAINTENANCE_START", "")
    await config_repo.set_config(pool, "MAINTENANCE_END", "")
    invalidate_maintenance_cache()

    await callback.message.edit_text(
        "<b>Maintenance mode ENABLED</b>\n\n"
        "All non-admin users will see a maintenance message.\n"
        "Toggle OFF from Settings when done.",
        reply_markup=admin_back_main(),
    )
    await callback.answer()


@router.callback_query(F.data == "maint_schedule")
async def cb_maint_schedule(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Ask admin for maintenance start time."""
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await state.set_state(AdminInput.waiting_maintenance_start)
    await callback.message.edit_text(
        "<b>Maintenance Schedule</b>\n\n"
        "Send start datetime (format: YYYY-MM-DD HH:MM)\n"
        "Timezone: UTC+7 (WIB)\n\n"
        "Example: 2026-02-25 02:00",
        reply_markup=admin_cancel(),
    )
    await callback.answer()


@router.message(AdminInput.waiting_maintenance_start)
async def on_maint_start_input(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return

    from datetime import datetime as dt, timezone as tz, timedelta
    text = (message.text or "").strip()
    try:
        naive = dt.strptime(text, "%Y-%m-%d %H:%M")
        # Interpret as WIB (UTC+7)
        wib = tz(timedelta(hours=7))
        start_dt = naive.replace(tzinfo=wib)
    except ValueError:
        await message.reply("Format salah. Gunakan: YYYY-MM-DD HH:MM\nContoh: 2026-02-25 02:00")
        return

    await state.update_data(maint_start=start_dt.isoformat())
    await state.set_state(AdminInput.waiting_maintenance_end)
    await message.answer(
        f"Start: <b>{text}</b> WIB\n\n"
        "Now send end datetime (same format: YYYY-MM-DD HH:MM):",
        reply_markup=admin_cancel(),
    )


@router.message(AdminInput.waiting_maintenance_end)
async def on_maint_end_input(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return

    from datetime import datetime as dt, timezone as tz, timedelta
    text = (message.text or "").strip()
    try:
        naive = dt.strptime(text, "%Y-%m-%d %H:%M")
        wib = tz(timedelta(hours=7))
        end_dt = naive.replace(tzinfo=wib)
    except ValueError:
        await message.reply("Format salah. Gunakan: YYYY-MM-DD HH:MM")
        return

    data = await state.get_data()
    start_iso = data["maint_start"]
    end_iso = end_dt.isoformat()

    pool = await get_pool()
    await config_repo.set_config(pool, "MAINTENANCE_MODE", "true")
    await config_repo.set_config(pool, "MAINTENANCE_START", start_iso)
    await config_repo.set_config(pool, "MAINTENANCE_END", end_iso)
    invalidate_maintenance_cache()
    await state.clear()

    start_display = dt.fromisoformat(start_iso).strftime("%Y-%m-%d %H:%M WIB")
    end_display = end_dt.strftime("%Y-%m-%d %H:%M WIB")

    await message.answer(
        "<b>Maintenance mode ENABLED (scheduled)</b>\n\n"
        f"From: {start_display}\n"
        f"Until: {end_display}\n\n"
        "Bot will auto-disable maintenance after the end time.",
        reply_markup=admin_back_main(),
    )


# ── Boolean Toggle Handler ─────────────────────

@router.callback_query(F.data.startswith("adm_toggle_"))
async def cb_config_toggle(callback: types.CallbackQuery) -> None:
    """Toggle a boolean config key between true/false and refresh settings."""
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    config_key = callback.data[11:]  # strip "adm_toggle_"
    pool = await get_pool()
    current = await config_repo.get_config(pool, config_key) or "false"
    is_on = current.strip().lower() in ("true", "1", "yes")
    new_value = "false" if is_on else "true"
    await config_repo.set_config(pool, config_key, new_value)

    status = "OFF" if is_on else "ON"
    await callback.answer(f"{config_key} -> {status}", show_alert=False)

    # Refresh settings menu
    config_rows = await config_repo.get_all_config(pool)
    await callback.message.edit_text(
        "<b>Settings</b>\n\nPilih pengaturan yang ingin diubah:",
        reply_markup=admin_settings_menu(config_rows),
    )


# ── Generic Config Key Editor ─────────────────

@router.callback_query(F.data.startswith("adm_cfg_"))
async def cb_config_edit_prompt(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Prompt admin to edit any config key."""
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    config_key = callback.data[8:]  # strip "adm_cfg_"
    pool = await get_pool()
    current_value = await config_repo.get_config(pool, config_key) or ""

    await state.set_state(AdminInput.waiting_config_value)
    await state.update_data(config_key=config_key)

    preview = current_value[:200] or "<i>empty</i>"
    await callback.message.edit_text(
        f"<b>Edit: {config_key}</b>\n\n"
        f"Nilai saat ini:\n<code>{preview}</code>\n\n"
        "Kirim nilai baru, atau kirim <code>-</code> untuk mengosongkan.",
        reply_markup=admin_cancel(),
    )
    await callback.answer()


@router.message(AdminInput.waiting_config_value)
async def on_config_value_input(message: types.Message, state: FSMContext) -> None:
    """Save a new value for any config key."""
    if not await _is_admin(message.from_user.id):
        return

    data = await state.get_data()
    config_key = data.get("config_key")
    if not config_key:
        await state.clear()
        return

    new_value = (message.text or "").strip()
    # Dash means clear the value
    if new_value == "-":
        new_value = ""

    pool = await get_pool()
    await config_repo.set_config(pool, config_key, new_value)
    await state.clear()

    preview = new_value[:100] or "<i>empty</i>"
    await message.answer(
        f"<b>{config_key}</b> diperbarui!\n\nNilai baru: <code>{preview}</code>",
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

    # Set referral count to required so status looks natural
    ref_required = await config_repo.get_required_referrals(pool)
    if user["referral_count"] < ref_required:
        await pool.execute(
            "UPDATE users SET referral_count = $1, last_updated = NOW() WHERE user_id = $2",
            ref_required, target_id,
        )

    await user_repo.set_verification_complete(pool, target_id)
    await user_repo.set_ready_to_join(pool, target_id, True)
    await state.clear()

    name = user["first_name"] or user["username"] or str(target_id)
    await message.answer(
        f"User <b>{name}</b> (ID: <code>{target_id}</code>) berhasil di-approve!",
        reply_markup=admin_back_main(),
    )

    # Generate invite link and notify the approved user
    try:
        target_lang = await user_repo.get_language(pool, target_id) or "id"
        bot: Bot = message.bot

        invite_expiry = await config_repo.get_invite_expiry(pool)
        invite = await bot.create_chat_invite_link(
            chat_id=settings.supergroup_id,
            member_limit=1,
            expire_date=int(time.time()) + invite_expiry,
        )

        await bot.send_message(
            target_id,
            t(target_lang, "admin_approved_you"),
            reply_markup=join_supergroup_keyboard(
                invite.invite_link,
                t(target_lang, "btn_join_supergroup"),
            ),
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
        f"Registered: {user['join_date'].strftime('%Y-%m-%d %H:%M')}\n"
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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CATEGORY / TOPIC MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.callback_query(F.data == "adm_categories")
async def cb_category_menu(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await state.clear()
    pool = await get_pool()
    topics = await topic_repo.get_all_topics(pool)
    count = len(topics)

    text = f"<b>Manage Categories</b>\n\nTotal categories: <b>{count}</b>\n\nPilih aksi:"
    await callback.message.edit_text(text, reply_markup=admin_category_menu())
    await callback.answer()


# ── List Categories ───────────────────────────

@router.callback_query(F.data == "adm_cat_list")
async def cb_category_list(callback: types.CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    pool = await get_pool()
    topics = await topic_repo.get_all_topics(pool)

    if not topics:
        text = "<b>Category List</b>\n\nBelum ada category. Tambahkan terlebih dahulu."
    else:
        lines = ["<b>Category List</b>\n"]
        for i, t_row in enumerate(topics, 1):
            all_tag = " [ALL]" if t_row["is_all"] else ""
            pfx = t_row.get("prefix") or "?"
            thread_tag = f" (thread: {t_row['thread_id']})" if t_row["thread_id"] else " (no thread)"
            lines.append(f"{i}. {t_row['name']} [<code>{pfx}</code>]{all_tag}{thread_tag}")
        text = "\n".join(lines)

    await callback.message.edit_text(text, reply_markup=admin_category_menu())
    await callback.answer()


# ── Add Category ──────────────────────────────

@router.callback_query(F.data == "adm_cat_add")
async def cb_category_add_prompt(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await state.set_state(AdminCategory.waiting_category_name)
    await callback.message.edit_text(
        "<b>Add Category</b>\n\n"
        "Kirim nama category baru (contoh: Action, Romance, Horror).\n\n"
        "Bot akan otomatis membuat topic baru di ZONA RATED.",
        reply_markup=admin_cancel(),
    )
    await callback.answer()


@router.message(AdminCategory.waiting_category_name)
async def on_category_name_input(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return

    name = (message.text or "").strip()
    if not name or len(name) > 100:
        await message.reply("Nama category harus 1-100 karakter.")
        return

    pool = await get_pool()

    # Check if category already exists
    existing = await topic_repo.get_topic_by_name(pool, name)
    if existing:
        await message.reply(
            f"Category '{existing['name']}' sudah ada. Kirim nama lain.",
        )
        return

    # Create forum topic in the supergroup
    bot: Bot = message.bot
    try:
        forum_topic = await bot.create_forum_topic(
            chat_id=settings.supergroup_id,
            name=name,
        )
        thread_id = forum_topic.message_thread_id

        # Close the topic so only admins/bot can post
        try:
            await bot.close_forum_topic(
                chat_id=settings.supergroup_id,
                message_thread_id=thread_id,
            )
        except Exception as e:
            logger.warning("Could not close topic '%s': %s", name, e)

    except Exception as e:
        logger.error("Failed to create forum topic '%s': %s", name, e)
        await message.reply(
            f"Gagal membuat topic di grup: {e}\n\nCoba lagi.",
            reply_markup=admin_cancel(),
        )
        return

    # Save to DB
    topic = await topic_repo.create_topic(pool, name, thread_id=thread_id)
    prefix = topic["prefix"]
    await state.clear()

    await message.answer(
        f"Category <b>{name}</b> berhasil ditambahkan!\n"
        f"Prefix: <code>{prefix}</code>\n"
        f"Forum topic created (thread_id: {thread_id})",
        reply_markup=admin_category_menu(),
    )


# ── Remove Category ──────────────────────────────

@router.callback_query(F.data == "adm_cat_remove")
async def cb_category_remove_list(callback: types.CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    pool = await get_pool()
    topics = await topic_repo.get_all_topics(pool)

    if not topics:
        await callback.answer("Belum ada category.", show_alert=True)
        return

    await callback.message.edit_text(
        "<b>Remove Category</b>\n\nPilih category yang ingin dihapus:",
        reply_markup=category_remove_keyboard(topics),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_cat_del_"))
async def cb_category_delete(callback: types.CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    topic_id = int(callback.data.split("_")[-1])
    pool = await get_pool()
    topic = await topic_repo.get_topic_by_id(pool, topic_id)

    if not topic:
        await callback.answer("Category tidak ditemukan.", show_alert=True)
        return

    name = topic["name"]

    # Try to delete the forum topic in Telegram
    if topic["thread_id"]:
        bot: Bot = callback.bot
        try:
            await bot.delete_forum_topic(
                chat_id=settings.supergroup_id,
                message_thread_id=topic["thread_id"],
            )
        except Exception as e:
            logger.warning("Could not delete forum topic for '%s': %s", name, e)

    await topic_repo.delete_topic(pool, topic_id)

    # Refresh the list
    topics = await topic_repo.get_all_topics(pool)
    if topics:
        await callback.message.edit_text(
            f"Category <b>{name}</b> dihapus!\n\nPilih category lain untuk dihapus:",
            reply_markup=category_remove_keyboard(topics),
        )
    else:
        await callback.message.edit_text(
            f"Category <b>{name}</b> dihapus!\n\nSemua category sudah dihapus.",
            reply_markup=admin_category_menu(),
        )
    await callback.answer()


# ── Set 'All' Topic ──────────────────────────────

@router.callback_query(F.data == "adm_cat_set_all")
async def cb_category_set_all_list(callback: types.CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    pool = await get_pool()
    topics = await topic_repo.get_all_topics(pool)

    if not topics:
        await callback.answer("Belum ada category. Tambahkan category dulu.", show_alert=True)
        return

    await callback.message.edit_text(
        "<b>Set 'All' Topic</b>\n\n"
        "Pilih category yang akan dijadikan topic 'All Videos'.\n"
        "Setiap video akan diposting juga ke topic ini.\n\n"
        "Category yang sudah menjadi 'All' ditandai >>",
        reply_markup=category_set_all_keyboard(topics),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_cat_all_"))
async def cb_category_mark_all(callback: types.CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    topic_id = int(callback.data.split("_")[-1])
    pool = await get_pool()

    # Clear existing 'All' flag
    await pool.execute("UPDATE topics SET is_all = FALSE WHERE is_all = TRUE")

    # Set the new one
    await pool.execute("UPDATE topics SET is_all = TRUE WHERE topic_id = $1", topic_id)

    topic = await topic_repo.get_topic_by_id(pool, topic_id)
    name = topic["name"] if topic else "?"

    await callback.message.edit_text(
        f"Topic <b>{name}</b> sekarang menjadi topic 'All Videos'!",
        reply_markup=admin_category_menu(),
    )
    await callback.answer()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SCHEDULED QUEUE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from bot.db import schedule_repo
from bot.keyboards.inline import schedule_queue_keyboard

@router.callback_query(F.data == "adm_sched_queue")
async def cb_sched_queue(callback: types.CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    pool = await get_pool()
    items = await schedule_repo.get_upcoming_schedules(pool, limit=20)

    if not items:
        await callback.message.edit_text(
            "<b>Scheduled Queue</b>\n\nNo scheduled videos.",
            reply_markup=admin_back_main(),
        )
        await callback.answer()
        return

    pending = sum(1 for i in items if i["status"] == "pending")
    posted = sum(1 for i in items if i["status"] == "posted")
    failed = sum(1 for i in items if i["status"] == "failed")

    text = (
        f"<b>Scheduled Queue</b>\n\n"
        f"Pending: {pending} | Posted: {posted} | Failed: {failed}\n\n"
        f"Click X to cancel a pending item."
    )

    await callback.message.edit_text(text, reply_markup=schedule_queue_keyboard(items))
    await callback.answer()


@router.callback_query(F.data.startswith("sched_cancel_"))
async def cb_sched_cancel(callback: types.CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    sid = int(callback.data.split("_")[-1])
    pool = await get_pool()
    ok = await schedule_repo.cancel_schedule(pool, sid)

    if ok:
        await callback.answer("Cancelled", show_alert=False)
    else:
        await callback.answer("Could not cancel (not pending?)", show_alert=True)

    # Refresh queue
    items = await schedule_repo.get_upcoming_schedules(pool, limit=20)
    if items:
        pending = sum(1 for i in items if i["status"] == "pending")
        posted = sum(1 for i in items if i["status"] == "posted")
        failed = sum(1 for i in items if i["status"] == "failed")
        text = (
            f"<b>Scheduled Queue</b>\n\n"
            f"Pending: {pending} | Posted: {posted} | Failed: {failed}\n\n"
            f"Click X to cancel a pending item."
        )
        await callback.message.edit_text(text, reply_markup=schedule_queue_keyboard(items))
    else:
        await callback.message.edit_text(
            "<b>Scheduled Queue</b>\n\nNo scheduled videos.",
            reply_markup=admin_back_main(),
        )


@router.callback_query(F.data.startswith("sched_info_"))
async def cb_sched_info(callback: types.CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    sid = int(callback.data.split("_")[-1])
    pool = await get_pool()
    item = await schedule_repo.get_schedule_by_id(pool, sid)

    if not item:
        await callback.answer("Not found", show_alert=True)
        return

    sched_at = item["scheduled_at"].strftime("%Y-%m-%d %H:%M") if item["scheduled_at"] else "N/A"
    posted_at = item["posted_at"].strftime("%Y-%m-%d %H:%M") if item.get("posted_at") else "N/A"
    err = item.get("error_message") or "None"

    text = (
        f"<b>Schedule #{sid}</b>\n\n"
        f"Title: {item['title']}\n"
        f"Category: {item['category'] or 'N/A'}\n"
        f"Status: {item['status']}\n"
        f"Scheduled: {sched_at}\n"
        f"Posted: {posted_at}\n"
        f"Error: {err[:200]}"
    )

    await callback.answer(text[:200], show_alert=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AUTO GET & RUN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from bot.states import AdminAutoRun
from bot.keyboards.inline import (
    autorun_category_keyboard,
    autorun_delay_keyboard,
    autorun_confirm_keyboard,
)

@router.callback_query(F.data == "adm_autorun")
async def cb_autorun_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Start Auto Get & Run — pick categories."""
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    pool = await get_pool()
    categories = await topic_repo.get_all_topics(pool)
    non_all = [g for g in categories if not g["is_all"]]

    if not non_all:
        await callback.message.edit_text(
            "<b>Auto Get & Run</b>\n\nNo categories found. Add categories first.",
            reply_markup=admin_back_main(),
        )
        await callback.answer()
        return

    await state.clear()
    await state.update_data(ar_selected=[])

    await callback.message.edit_text(
        "<b>Auto Get & Run</b>\n\n"
        "Select categories to scan from Bunny Storage.\n"
        "Folder names in storage must match category names.",
        reply_markup=autorun_category_keyboard(categories),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ar_cat_") & ~F.data.in_({"ar_cat_done", "ar_cat_all"}))
async def cb_autorun_cat_toggle(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    topic_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    selected: list = data.get("ar_selected", [])

    if topic_id in selected:
        selected.remove(topic_id)
    else:
        selected.append(topic_id)

    await state.update_data(ar_selected=selected)

    pool = await get_pool()
    categories = await topic_repo.get_all_topics(pool)

    await callback.message.edit_text(
        "<b>Auto Get & Run</b>\n\n"
        "Select categories to scan from Bunny Storage.",
        reply_markup=autorun_category_keyboard(categories, selected),
    )
    await callback.answer()


@router.callback_query(F.data == "ar_cat_all")
async def cb_autorun_cat_select_all(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    pool = await get_pool()
    categories = await topic_repo.get_all_topics(pool)
    non_all = [g for g in categories if not g["is_all"]]
    selected = [g["topic_id"] for g in non_all]

    await state.update_data(ar_selected=selected)

    await callback.message.edit_text(
        "<b>Auto Get & Run</b>\n\n"
        "All categories selected.",
        reply_markup=autorun_category_keyboard(categories, selected),
    )
    await callback.answer()


@router.callback_query(F.data == "ar_cat_done")
async def cb_autorun_cat_done(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    data = await state.get_data()
    selected = data.get("ar_selected", [])
    if not selected:
        await callback.answer("Select at least one category.", show_alert=True)
        return

    await callback.message.edit_text(
        "<b>Auto Get & Run — Delay</b>\n\n"
        "Choose delay between posts:",
        reply_markup=autorun_delay_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ar_delay_") & ~F.data.in_({"ar_delay_custom"}))
async def cb_autorun_delay_preset(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    minutes = int(callback.data.split("_")[-1])
    await state.update_data(ar_delay_minutes=minutes)

    # Now scan and show summary
    await _autorun_scan_and_confirm(callback, state, minutes)
    await callback.answer()


@router.callback_query(F.data == "ar_delay_custom")
async def cb_autorun_delay_custom(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await state.set_state(AdminAutoRun.waiting_delay)
    await callback.message.edit_text(
        "<b>Auto Get & Run — Custom Delay</b>\n\n"
        "Send delay in minutes (e.g. 45):",
        reply_markup=admin_cancel(),
    )
    await callback.answer()


@router.message(AdminAutoRun.waiting_delay)
async def on_autorun_delay_input(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return

    try:
        minutes = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.reply("Send a valid number of minutes.")
        return

    if minutes < 1 or minutes > 1440:
        await message.reply("Minutes must be between 1 and 1440 (24 hours).")
        return

    await state.update_data(ar_delay_minutes=minutes)
    await state.set_state(AdminAutoRun.confirming)

    # Scan and show summary (via fake callback for message context)
    await _autorun_scan_and_confirm_msg(message, state, minutes)


async def _autorun_scan_and_confirm(
    callback: types.CallbackQuery, state: FSMContext, delay_minutes: int
) -> None:
    """Scan Bunny Storage and show summary for confirmation."""
    from bot.utils.bunny_storage import list_category_videos

    pool = await get_pool()
    data = await state.get_data()
    selected_ids = data.get("ar_selected", [])

    # Resolve category names
    categories = []
    for tid in selected_ids:
        topic = await topic_repo.get_topic_by_id(pool, tid)
        if topic:
            categories.append(topic)

    # Get already-posted and scheduled URLs for exclusion
    posted_urls = await video_repo.get_all_file_urls(pool)
    scheduled_urls = await schedule_repo.get_scheduled_urls(pool)
    exclude_urls = posted_urls | scheduled_urls

    # Scan storage
    total_new = 0
    category_summary = []
    all_new_videos = []

    for cat in categories:
        cat_name = cat["name"]
        try:
            videos = await list_category_videos(cat_name)
        except Exception as e:
            logger.warning("Auto Get & Run: failed to scan '%s': %s", cat_name, e)
            category_summary.append(f"  {cat_name}: ERROR ({e})")
            continue

        new_videos = [v for v in videos if v["url"] not in exclude_urls]
        total_new += len(new_videos)
        category_summary.append(f"  {cat_name}: {len(new_videos)} new / {len(videos)} total")

        for v in new_videos:
            all_new_videos.append({
                "url": v["url"],
                "title": v["title"],
                "category": cat_name,
                "topic_id": cat["topic_id"],
            })

    await state.update_data(ar_new_videos=all_new_videos)
    await state.set_state(AdminAutoRun.confirming)

    summary = "\n".join(category_summary) or "  No categories scanned"

    await callback.message.edit_text(
        f"<b>Auto Get & Run — Summary</b>\n\n"
        f"Delay: {delay_minutes} minutes\n"
        f"New videos found: <b>{total_new}</b>\n\n"
        f"Breakdown:\n{summary}\n\n"
        f"Confirm to schedule all {total_new} videos?",
        reply_markup=autorun_confirm_keyboard(),
    )


async def _autorun_scan_and_confirm_msg(
    message: types.Message, state: FSMContext, delay_minutes: int
) -> None:
    """Same as above but triggered from a message context."""
    from bot.utils.bunny_storage import list_category_videos

    pool = await get_pool()
    data = await state.get_data()
    selected_ids = data.get("ar_selected", [])

    categories = []
    for tid in selected_ids:
        topic = await topic_repo.get_topic_by_id(pool, tid)
        if topic:
            categories.append(topic)

    posted_urls = await video_repo.get_all_file_urls(pool)
    scheduled_urls = await schedule_repo.get_scheduled_urls(pool)
    exclude_urls = posted_urls | scheduled_urls

    total_new = 0
    category_summary = []
    all_new_videos = []

    for cat in categories:
        cat_name = cat["name"]
        try:
            videos = await list_category_videos(cat_name)
        except Exception as e:
            logger.warning("Auto Get & Run: failed to scan '%s': %s", cat_name, e)
            category_summary.append(f"  {cat_name}: ERROR ({e})")
            continue

        new_videos = [v for v in videos if v["url"] not in exclude_urls]
        total_new += len(new_videos)
        category_summary.append(f"  {cat_name}: {len(new_videos)} new / {len(videos)} total")

        for v in new_videos:
            all_new_videos.append({
                "url": v["url"],
                "title": v["title"],
                "category": cat_name,
                "topic_id": cat["topic_id"],
            })

    await state.update_data(ar_new_videos=all_new_videos)

    summary = "\n".join(category_summary) or "  No categories scanned"

    await message.answer(
        f"<b>Auto Get & Run — Summary</b>\n\n"
        f"Delay: {delay_minutes} minutes\n"
        f"New videos found: <b>{total_new}</b>\n\n"
        f"Breakdown:\n{summary}\n\n"
        f"Confirm to schedule all {total_new} videos?",
        reply_markup=autorun_confirm_keyboard(),
    )


@router.callback_query(AdminAutoRun.confirming, F.data == "ar_confirm")
async def cb_autorun_confirm(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    from datetime import datetime as dt, timedelta, timezone as tz

    data = await state.get_data()
    await state.clear()

    delay_minutes = data.get("ar_delay_minutes", 60)
    new_videos = data.get("ar_new_videos", [])

    if not new_videos:
        await callback.message.edit_text(
            "<b>Auto Get & Run</b>\n\nNo new videos to schedule.",
            reply_markup=admin_back_main(),
        )
        await callback.answer()
        return

    pool = await get_pool()
    now = dt.now(tz.utc)
    created = 0

    for i, vid in enumerate(new_videos):
        sched_time = now + timedelta(minutes=delay_minutes * (i + 1))
        topic_ids_str = str(vid["topic_id"])

        await schedule_repo.create_scheduled_video(
            pool,
            title=vid["title"],
            category=vid["category"],
            description=None,
            file_url=vid["url"],
            thumbnail_b64=None,
            thumbnail_file_id=None,
            affiliate_link=None,
            topic_ids=topic_ids_str,
            scheduled_at=sched_time,
            created_by=callback.from_user.id,
        )
        created += 1

    first_time = (now + timedelta(minutes=delay_minutes)).strftime("%Y-%m-%d %H:%M UTC")
    last_time = (now + timedelta(minutes=delay_minutes * len(new_videos))).strftime("%Y-%m-%d %H:%M UTC")

    await callback.message.edit_text(
        f"<b>Auto Get & Run — Done</b>\n\n"
        f"Scheduled: <b>{created}</b> videos\n"
        f"Delay: {delay_minutes} min between posts\n"
        f"First post at: {first_time}\n"
        f"Last post at: {last_time}\n\n"
        f"View progress in Scheduled Queue.",
        reply_markup=admin_back_main(),
    )
    await callback.answer()
