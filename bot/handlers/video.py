"""Video management — add-video wizard (admin) + download flow (users).

Admin flow:
    /addvideo  OR  Admin Panel > Add Video
    → title → genre picker → description → video file/URL
    → affiliate (optional) → confirm → posts to supergroup

Download flow:
    User clicks "Download" on a video post in the supergroup
    → affiliate link gate → video delivered to private chat
"""

from __future__ import annotations

import base64
import logging

from aiogram import Bot, Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile

from bot.config import settings
from bot.db.pool import get_pool
from bot.db import config_repo, user_repo, topic_repo, video_repo
from bot.keyboards.inline import (
    genre_picker_keyboard,
    video_skip_keyboard,
    video_confirm_keyboard,
    download_button,
    video_download_button,
    admin_back_main,
    admin_cancel,
    thumbnail_preview_keyboard,
)
from bot.states import AdminVideo
from bot.i18n import t
from bot.utils.thumbnail import extract_thumbnail
from bot.utils.shortener import shorten_url

logger = logging.getLogger(__name__)

router = Router(name="video")


# ═══════════════════════════════════════════════
# Guard
# ═══════════════════════════════════════════════

async def _is_admin(user_id: int) -> bool:
    pool = await get_pool()
    admin_ids = await config_repo.get_admin_ids(pool)
    return user_id in admin_ids


# ═══════════════════════════════════════════════
# ADD VIDEO WIZARD
# ═══════════════════════════════════════════════

# ── Entry point: /addvideo or callback ────────

@router.message(Command("addvideo"))
async def cmd_addvideo(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return
    await _start_video_wizard(message, state)


@router.callback_query(F.data == "adm_addvideo")
async def cb_addvideo(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await callback.message.edit_text(
        "<b>Add Video</b>\n\n"
        "Kirim judul video:",
        reply_markup=admin_cancel(),
    )
    await state.set_state(AdminVideo.waiting_title)
    await callback.answer()


async def _start_video_wizard(message: types.Message, state: FSMContext) -> None:
    """Begin the add-video wizard."""
    await state.clear()
    await state.set_state(AdminVideo.waiting_title)
    await message.answer(
        "<b>Add Video</b>\n\n"
        "Kirim judul video:",
        reply_markup=admin_cancel(),
    )


# ── Cancel wizard ─────────────────────────────

@router.callback_query(F.data == "vid_cancel")
async def cb_vid_cancel(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Video wizard dibatalkan.")
    await callback.answer()


# ── Step 1: Title ─────────────────────────────

@router.message(AdminVideo.waiting_title)
async def on_video_title(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return

    title = (message.text or "").strip()
    if not title:
        await message.reply("Judul tidak boleh kosong.")
        return

    await state.update_data(title=title, selected_genres=[])

    # Show genre picker
    pool = await get_pool()
    genres = await topic_repo.get_all_topics(pool)

    # Filter out genres that are only "All" with no other genres
    non_all = [g for g in genres if not g["is_all"]]
    if not non_all:
        await message.reply(
            "Belum ada genre. Tambahkan genre terlebih dahulu via Admin Panel > Manage Genres.\n\n"
            "Wizard dibatalkan.",
        )
        await state.clear()
        return

    await state.set_state(AdminVideo.waiting_genre)
    await message.answer(
        "<b>Step 2/6: Pilih Genre</b>\n\n"
        "Tap genre untuk memilih/batal pilih (bisa lebih dari 1).\n"
        "Tekan <b>Done</b> setelah selesai memilih.",
        reply_markup=genre_picker_keyboard(genres),
    )


# ── Step 2: Genre (multi-select toggle) ───────

@router.callback_query(AdminVideo.waiting_genre, F.data == "vid_genre_done")
async def on_video_genre_done(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Confirm genre selection and move to description step."""
    data = await state.get_data()
    selected: list = data.get("selected_genres", [])

    if not selected:
        await callback.answer("Pilih minimal 1 genre.", show_alert=True)
        return

    # Resolve genre details
    pool = await get_pool()
    genres_data = []
    genre_names = []
    for tid in selected:
        topic = await topic_repo.get_topic_by_id(pool, tid)
        if topic:
            genres_data.append({
                "topic_id": topic["topic_id"],
                "name": topic["name"],
                "thread_id": topic["thread_id"],
                "prefix": topic.get("prefix"),
            })
            genre_names.append(topic["name"])

    await state.update_data(
        genres=genres_data,
        genre_names=genre_names,
    )

    names_str = ", ".join(genre_names)
    await state.set_state(AdminVideo.waiting_description)
    await callback.message.edit_text(
        f"Genre: <b>{names_str}</b>\n\n"
        "<b>Step 3/6: Deskripsi</b>\n\n"
        "Kirim deskripsi video (atau klik Skip):",
        reply_markup=video_skip_keyboard(),
    )
    await callback.answer()


@router.callback_query(AdminVideo.waiting_genre, F.data.startswith("vid_genre_"))
async def on_video_genre_toggle(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Toggle a genre selection on/off."""
    topic_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    selected: list = data.get("selected_genres", [])

    # Toggle
    if topic_id in selected:
        selected.remove(topic_id)
    else:
        selected.append(topic_id)

    await state.update_data(selected_genres=selected)

    # Refresh the keyboard
    pool = await get_pool()
    genres = await topic_repo.get_all_topics(pool)

    sel_names = []
    for g in genres:
        if g["topic_id"] in selected:
            sel_names.append(g["name"])
    sel_text = ", ".join(sel_names) if sel_names else "<i>belum dipilih</i>"

    await callback.message.edit_text(
        "<b>Step 2/6: Pilih Genre</b>\n\n"
        f"Dipilih: {sel_text}\n\n"
        "Tap genre untuk memilih/batal pilih.\n"
        "Tekan <b>Done</b> setelah selesai memilih.",
        reply_markup=genre_picker_keyboard(genres, selected),
    )
    await callback.answer()


# ── Step 3: Description ──────────────────────

@router.callback_query(AdminVideo.waiting_description, F.data == "vid_skip")
async def on_video_desc_skip(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.update_data(description=None)
    await state.set_state(AdminVideo.waiting_file)
    await callback.message.edit_text(
        "<b>Step 4/6: Video File</b>\n\n"
        "Kirim file video atau URL video:",
        reply_markup=admin_cancel(),
    )
    await callback.answer()


@router.message(AdminVideo.waiting_description)
async def on_video_description(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return

    desc = (message.text or "").strip()
    if not desc:
        await message.reply("Kirim deskripsi atau klik Skip.")
        return

    await state.update_data(description=desc)
    await state.set_state(AdminVideo.waiting_file)
    await message.answer(
        "<b>Step 4/6: Video File</b>\n\n"
        "Kirim file video atau URL video:",
        reply_markup=admin_cancel(),
    )


# ── Step 4: Video file/URL ───────────────────

@router.message(AdminVideo.waiting_file)
async def on_video_file(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return

    file_url = None
    is_telegram_file = False

    # Check if admin sent a video file
    if message.video:
        file_url = message.video.file_id
        is_telegram_file = True
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("video/"):
        file_url = message.document.file_id
        is_telegram_file = True
    elif message.text:
        url = message.text.strip()
        if url.startswith(("http://", "https://")):
            file_url = url
        else:
            await message.reply("Kirim file video langsung atau paste URL (http/https).")
            return
    else:
        await message.reply("Kirim file video atau URL.")
        return

    await state.update_data(file_url=file_url, is_telegram_file=is_telegram_file)

    # For Telegram file uploads, skip thumbnail step (already has preview)
    if is_telegram_file:
        await state.set_state(AdminVideo.waiting_affiliate)
        await message.answer(
            "<b>Step 6/6: Affiliate Link (opsional)</b>\n\n"
            "Kirim affiliate link khusus untuk video ini.\n"
            "Atau klik Skip untuk menggunakan affiliate link global.",
            reply_markup=video_skip_keyboard(),
        )
        return

    # For URL videos, auto-extract thumbnail at 1 second
    await message.answer("Mengekstrak thumbnail dari video...")
    thumb_data = await extract_thumbnail(file_url, timestamp_seconds=1)

    if thumb_data:
        photo = BufferedInputFile(thumb_data, filename="thumbnail.jpg")
        await message.answer_photo(
            photo=photo,
            caption=(
                "<b>Step 5/6: Thumbnail Preview</b>\n\n"
                "Frame dari detik ke-1 video.\n"
                "Pilih opsi atau kirim foto sendiri sebagai thumbnail."
            ),
            reply_markup=thumbnail_preview_keyboard(),
        )
        thumb_b64 = base64.b64encode(thumb_data).decode()
        await state.update_data(thumbnail_b64=thumb_b64)
        await state.set_state(AdminVideo.waiting_thumbnail)
    else:
        # Failed to extract — skip thumbnail
        logger.warning("Thumbnail extraction failed for %s", file_url[:80])
        await state.set_state(AdminVideo.waiting_affiliate)
        await message.answer(
            "Gagal mengekstrak thumbnail. Lanjut tanpa thumbnail.\n\n"
            "<b>Step 6/6: Affiliate Link (opsional)</b>\n\n"
            "Kirim affiliate link khusus untuk video ini.\n"
            "Atau klik Skip untuk menggunakan affiliate link global.",
            reply_markup=video_skip_keyboard(),
        )


# ── Step 5: Thumbnail preview / change / upload ──

@router.callback_query(AdminVideo.waiting_thumbnail, F.data == "vid_thumb_ok")
async def cb_vid_thumb_ok(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Admin accepts the auto-extracted thumbnail."""
    await state.set_state(AdminVideo.waiting_affiliate)
    await callback.message.answer(
        "<b>Step 6/6: Affiliate Link (opsional)</b>\n\n"
        "Kirim affiliate link khusus untuk video ini.\n"
        "Atau klik Skip untuk menggunakan affiliate link global.",
        reply_markup=video_skip_keyboard(),
    )
    await callback.answer()


@router.callback_query(AdminVideo.waiting_thumbnail, F.data == "vid_thumb_change")
async def cb_vid_thumb_change(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Admin wants to pick a different timestamp for thumbnail."""
    await state.set_state(AdminVideo.waiting_thumb_ts)
    await callback.message.answer(
        "Kirim detik yang diinginkan (contoh: 5 untuk frame pada detik ke-5):",
        reply_markup=admin_cancel(),
    )
    await callback.answer()


@router.callback_query(AdminVideo.waiting_thumbnail, F.data == "vid_thumb_skip")
async def cb_vid_thumb_skip(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Admin skips the thumbnail — post will be text-only."""
    await state.update_data(thumbnail_b64=None)
    await state.set_state(AdminVideo.waiting_affiliate)
    await callback.message.answer(
        "<b>Step 6/6: Affiliate Link (opsional)</b>\n\n"
        "Kirim affiliate link khusus untuk video ini.\n"
        "Atau klik Skip untuk menggunakan affiliate link global.",
        reply_markup=video_skip_keyboard(),
    )
    await callback.answer()


@router.message(AdminVideo.waiting_thumbnail, F.photo)
async def on_thumb_custom_photo(message: types.Message, state: FSMContext) -> None:
    """Admin uploads their own photo to use as thumbnail."""
    if not await _is_admin(message.from_user.id):
        return

    photo = message.photo[-1]  # Largest resolution
    file = await message.bot.get_file(photo.file_id)
    bio = await message.bot.download_file(file.file_path)
    thumb_data = bio.read()

    thumb_b64 = base64.b64encode(thumb_data).decode()
    await state.update_data(thumbnail_b64=thumb_b64)

    await state.set_state(AdminVideo.waiting_affiliate)
    await message.answer(
        "Thumbnail custom diterima!\n\n"
        "<b>Step 6/6: Affiliate Link (opsional)</b>\n\n"
        "Kirim affiliate link khusus untuk video ini.\n"
        "Atau klik Skip untuk menggunakan affiliate link global.",
        reply_markup=video_skip_keyboard(),
    )


@router.message(AdminVideo.waiting_thumb_ts)
async def on_thumb_timestamp(message: types.Message, state: FSMContext) -> None:
    """Admin sends a number for the timestamp to extract thumbnail at."""
    if not await _is_admin(message.from_user.id):
        return

    text = (message.text or "").strip()
    try:
        ts = int(text)
    except ValueError:
        await message.reply("Kirim angka (detik). Contoh: 5")
        return

    if ts < 0:
        await message.reply("Angka harus positif.")
        return

    data = await state.get_data()
    file_url = data["file_url"]

    await message.answer("Mengekstrak thumbnail...")
    thumb_data = await extract_thumbnail(file_url, timestamp_seconds=ts)

    if thumb_data:
        photo = BufferedInputFile(thumb_data, filename="thumbnail.jpg")
        await message.answer_photo(
            photo=photo,
            caption=(
                f"<b>Step 5/6: Thumbnail Preview</b>\n\n"
                f"Frame dari detik ke-{ts} video.\n"
                "Pilih opsi atau kirim foto sendiri sebagai thumbnail."
            ),
            reply_markup=thumbnail_preview_keyboard(),
        )
        thumb_b64 = base64.b64encode(thumb_data).decode()
        await state.update_data(thumbnail_b64=thumb_b64)
        await state.set_state(AdminVideo.waiting_thumbnail)
    else:
        await message.answer(
            f"Gagal mengekstrak frame dari detik ke-{ts}.\n"
            "Coba angka lain atau kirim foto sendiri:",
            reply_markup=admin_cancel(),
        )


# ── Step 6: Affiliate (optional) ─────────────

@router.callback_query(AdminVideo.waiting_affiliate, F.data == "vid_skip")
async def on_video_aff_skip(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.update_data(affiliate_link=None)
    await _show_video_preview(callback.message, state, edit=True)
    await callback.answer()


@router.message(AdminVideo.waiting_affiliate)
async def on_video_affiliate(message: types.Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        return

    url = (message.text or "").strip()
    if not url.startswith(("http://", "https://")):
        await message.reply("URL harus dimulai dengan http:// atau https:// atau klik Skip.")
        return

    await state.update_data(affiliate_link=url)
    await _show_video_preview(message, state, edit=False)


# ── Preview ───────────────────────────────────

async def _show_video_preview(message: types.Message, state: FSMContext, *, edit: bool) -> None:
    """Show a preview of the video details before confirming."""
    data = await state.get_data()

    title = data.get("title", "-")
    genre_names = data.get("genre_names", [])
    genre = ", ".join(genre_names) if genre_names else "-"
    desc = data.get("description") or "<i>tidak ada</i>"
    file_url = data.get("file_url", "-")
    is_tg = data.get("is_telegram_file", False)
    aff = data.get("affiliate_link") or "<i>global</i>"

    file_display = "Telegram file" if is_tg else file_url
    if len(file_display) > 60:
        file_display = file_display[:57] + "..."

    has_thumb = "Ya" if data.get("thumbnail_b64") else "Tidak"

    text = (
        "<b>Preview Video</b>\n\n"
        f"Title: <b>{title}</b>\n"
        f"Genre: <b>{genre}</b>\n"
        f"Description: {desc}\n"
        f"File: {file_display}\n"
        f"Thumbnail: {has_thumb}\n"
        f"Affiliate: {aff}\n\n"
        "<i>Code akan di-generate otomatis saat posting.</i>\n\n"
        "Konfirmasi untuk posting?"
    )

    await state.set_state(AdminVideo.confirming)
    if edit:
        await message.edit_text(text, reply_markup=video_confirm_keyboard())
    else:
        await message.answer(text, reply_markup=video_confirm_keyboard())


# ── Confirm & post ────────────────────────────

@router.callback_query(AdminVideo.confirming, F.data == "vid_confirm")
async def on_video_confirm(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    data = await state.get_data()
    await state.clear()

    title = data["title"]
    genres_data = data.get("genres", [])
    genre_names = data.get("genre_names", [])
    genre_display = ", ".join(genre_names) if genre_names else "-"
    description = data.get("description")
    file_url = data["file_url"]
    is_telegram_file = data.get("is_telegram_file", False)
    affiliate_link = data.get("affiliate_link")

    # Decode thumbnail if present
    thumbnail_b64 = data.get("thumbnail_b64")
    thumbnail_data = base64.b64decode(thumbnail_b64) if thumbnail_b64 else None

    pool = await get_pool()
    bot: Bot = callback.bot

    # Use the first genre name for video code prefix and primary category
    primary_genre = genre_names[0] if genre_names else "Unknown"

    # Save video to DB first (without message_id)
    video = await video_repo.create_video(
        pool,
        title=title,
        category=genre_display,
        description=description,
        file_url=file_url,
        affiliate_link=affiliate_link,
    )
    vid_id = video["video_id"]
    vid_code = video["code"]

    # Shorten URL if it's an external link (not a Telegram file_id)
    if not is_telegram_file:
        short = await shorten_url(file_url)
        if short:
            await video_repo.set_shortened_url(pool, vid_id, short)

    # Build caption
    caption_lines = [f"<b>{title}</b>"]
    caption_lines.append(f"Code: <code>{vid_code}</code>")
    if description:
        caption_lines.append(f"\n{description}")
    caption_lines.append(f"\nGenre: {genre_display}")
    caption = "\n".join(caption_lines)

    # Post to each selected genre topic
    genre_results = []
    first_msg_id = None
    first_thread_id = None
    thumb_file_id = None  # Reuse Telegram file_id after first upload
    for g in genres_data:
        thread_id = g.get("thread_id")
        if thread_id:
            msg_id, fid = await _post_to_topic(
                bot, thread_id, caption, file_url, is_telegram_file, vid_id,
                thumbnail_data=thumbnail_data if not thumb_file_id else None,
                thumbnail_file_id=thumb_file_id,
            )
            if fid and not thumb_file_id:
                thumb_file_id = fid
            genre_results.append((g["name"], msg_id))
            if msg_id and first_msg_id is None:
                first_msg_id = msg_id
                first_thread_id = thread_id

    # Post to the "All" topic
    all_topic = await topic_repo.get_all_topic(pool)
    all_msg_id = None
    if all_topic and all_topic["thread_id"]:
        all_msg_id, fid = await _post_to_topic(
            bot, all_topic["thread_id"], caption, file_url, is_telegram_file, vid_id,
            thumbnail_data=thumbnail_data if not thumb_file_id else None,
            thumbnail_file_id=thumb_file_id,
        )
        if fid and not thumb_file_id:
            thumb_file_id = fid

    # Update video record with the first genre message_id and thumbnail
    if first_msg_id:
        await video_repo.set_message_id(pool, vid_id, first_msg_id, first_thread_id)
    if thumb_file_id:
        await video_repo.set_thumbnail_file_id(pool, vid_id, thumb_file_id)

    # Build result text
    genre_status = "\n".join(
        f"  {name}: {'OK' if mid else 'GAGAL'}" for name, mid in genre_results
    ) or "  (no topics)"

    await callback.message.edit_text(
        f"Video <b>{title}</b> berhasil diposting!\n\n"
        f"Code: <code>{vid_code}</code>\n"
        f"Video ID: {vid_id}\n"
        f"Genre topics:\n{genre_status}\n"
        f"All topic: {'OK' if all_msg_id else ('GAGAL' if all_topic else 'N/A')}",
        reply_markup=admin_back_main(),
    )
    await callback.answer()


async def _post_to_topic(
    bot: Bot,
    thread_id: int,
    caption: str,
    file_url: str,
    is_telegram_file: bool,
    video_id: int,
    thumbnail_data: bytes | None = None,
    thumbnail_file_id: str | None = None,
) -> tuple[int | None, str | None]:
    """Post a video to a specific forum topic.

    Returns (message_id, thumbnail_file_id) or (None, None).
    """
    try:
        if is_telegram_file:
            msg = await bot.send_video(
                chat_id=settings.supergroup_id,
                message_thread_id=thread_id,
                video=file_url,
                caption=caption,
                reply_markup=download_button(video_id),
            )
            return msg.message_id, None

        # URL-based video — use thumbnail photo if available
        if thumbnail_file_id:
            msg = await bot.send_photo(
                chat_id=settings.supergroup_id,
                message_thread_id=thread_id,
                photo=thumbnail_file_id,
                caption=caption,
                reply_markup=download_button(video_id),
            )
            return msg.message_id, thumbnail_file_id

        if thumbnail_data:
            photo_input = BufferedInputFile(thumbnail_data, filename="thumb.jpg")
            msg = await bot.send_photo(
                chat_id=settings.supergroup_id,
                message_thread_id=thread_id,
                photo=photo_input,
                caption=caption,
                reply_markup=download_button(video_id),
            )
            fid = msg.photo[-1].file_id if msg.photo else None
            return msg.message_id, fid

        # No thumbnail — plain text (no raw URL exposed)
        text = caption
        msg = await bot.send_message(
            chat_id=settings.supergroup_id,
            message_thread_id=thread_id,
            text=text,
            reply_markup=download_button(video_id),
        )
        return msg.message_id, None
    except Exception as e:
        logger.error("Failed to post video to thread %s: %s", thread_id, e)
        return None, None


# ═══════════════════════════════════════════════
# DOWNLOAD FLOW
# Video delivery is now handled automatically by
# the web server (bot/web.py) when user opens the
# verified redirect link.  The old "Done" callback
# is kept only as a fallback for sessions created
# before the redirect system was deployed.
# ═══════════════════════════════════════════════

# ── Legacy affiliate done callback (fallback) ─

@router.callback_query(F.data.startswith("aff_done_"))
async def cb_affiliate_done(callback: types.CallbackQuery) -> None:
    """Legacy fallback: user clicked 'Done' on old-style sessions."""
    session_id = callback.data[9:]  # strip "aff_done_"

    pool = await get_pool()
    session = await video_repo.get_download_session(pool, session_id)

    user_id = callback.from_user.id
    user = await user_repo.get_user(pool, user_id)
    lang = (user["language"] if user else None) or "id"

    if not session:
        await callback.answer(t(lang, "dl_session_expired"), show_alert=True)
        return

    if session["user_id"] != user_id:
        await callback.answer("Session invalid.", show_alert=True)
        return

    from datetime import datetime, timezone
    if session["expires_at"] and session["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        await callback.answer(t(lang, "dl_session_expired"), show_alert=True)
        return

    if session["video_sent"]:
        await callback.answer("Video sudah dikirim sebelumnya.", show_alert=True)
        return

    video_id = session["video_id"]
    video = await video_repo.get_video(pool, video_id)

    if not video:
        await callback.answer(t(lang, "dl_error"), show_alert=True)
        return

    bot: Bot = callback.bot

    await video_repo.mark_affiliate_visited(pool, session_id)

    try:
        await _deliver_video(bot, user_id, video, lang)
        await video_repo.mark_video_sent(pool, session_id)
        await video_repo.increment_downloads(pool, video_id)
        await video_repo.log_download(pool, user_id, video_id, session_id, True)
        await callback.message.edit_text(t(lang, "dl_video_sent"))
        await callback.answer()
    except Exception as e:
        logger.error("Failed to deliver video %s to user %s: %s", video_id, user_id, e)
        await callback.answer(t(lang, "dl_error"), show_alert=True)


# ── Deliver video to private chat ────────────

async def _deliver_video(
    bot: Bot, user_id: int, video: dict, lang: str
) -> None:
    """Send the actual video file or URL to user's private chat."""
    file_url = video["file_url"]
    title = video["title"]
    code = video.get("code", "")
    category = video.get("category", "")
    description = video.get("description")

    # Build caption matching topic post style
    caption_lines = [f"<b>{title}</b>"]
    if code:
        caption_lines.append(f"Code: <code>{code}</code>")
    if description:
        caption_lines.append(f"\n{description}")
    if category:
        caption_lines.append(f"\nGenre: {category}")
    caption = "\n".join(caption_lines)

    # Check if it's a Telegram file_id (no http prefix)
    if not file_url.startswith(("http://", "https://")):
        # It's a Telegram file_id — send as video
        await bot.send_video(
            chat_id=user_id,
            video=file_url,
            caption=caption,
        )
    else:
        # Build a signed CDN URL when the file lives on Bunny CDN
        from bot.config import settings as _cfg
        from bot.utils.cdn import sign_bunny_url

        if (
            _cfg.bunny_cdn_hostname
            and _cfg.bunny_token_key
            and file_url.startswith(_cfg.bunny_cdn_hostname)
        ):
            delivery_url = sign_bunny_url(
                file_url,
                _cfg.bunny_cdn_hostname,
                _cfg.bunny_token_key,
            )
        else:
            # Non-CDN URL — use shortened link if available
            delivery_url = video.get("shortened_url") or file_url
        thumb_fid = video.get("thumbnail_file_id")

        if thumb_fid:
            # Send thumbnail photo with Download Video button
            await bot.send_photo(
                chat_id=user_id,
                photo=thumb_fid,
                caption=caption,
                reply_markup=video_download_button(delivery_url),
            )
        else:
            # No thumbnail — send text with Download Video button
            await bot.send_message(
                chat_id=user_id,
                text=caption,
                reply_markup=video_download_button(delivery_url),
            )
