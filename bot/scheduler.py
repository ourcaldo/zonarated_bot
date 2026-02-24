"""Background scheduler — periodic tasks that run alongside polling.

Tasks:
  - check_newly_qualified: every 60s, scans for users who now meet the
    referral requirement but haven't been notified yet.
  - check_maintenance_auto_disable: auto-disables maintenance when window ends.
  - process_scheduled_videos: posts scheduled videos when their time arrives.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from datetime import datetime, timezone

from aiogram import Bot

from bot.db.pool import get_pool
from bot.db import config_repo, user_repo, topic_repo, video_repo, schedule_repo
from bot.keyboards.inline import gabung_grup_keyboard, download_button
from bot.i18n import t
from bot.config import settings

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


async def _check_maintenance_auto_disable() -> None:
    """Auto-disable maintenance mode if the scheduled end time has passed."""
    pool = await get_pool()
    raw = await config_repo.get_config(pool, "MAINTENANCE_MODE")
    if not raw or raw.strip().lower() not in ("true", "1", "yes"):
        return

    end_str = await config_repo.get_config(pool, "MAINTENANCE_END")
    if not end_str:
        return

    try:
        end_dt = datetime.fromisoformat(end_str)
    except ValueError:
        return

    if datetime.now(timezone.utc) > end_dt.astimezone(timezone.utc):
        await config_repo.set_config(pool, "MAINTENANCE_MODE", "false")
        await config_repo.set_config(pool, "MAINTENANCE_START", "")
        await config_repo.set_config(pool, "MAINTENANCE_END", "")
        logger.info("Scheduler: maintenance mode auto-disabled (end time passed)")


async def _process_scheduled_videos(bot: Bot) -> None:
    """Post scheduled videos that are due."""
    from bot.utils.shortener import shorten_url
    from bot.utils.cdn import sign_bunny_url
    from bot.utils.thumbnail import extract_thumbnail
    from aiogram.types import BufferedInputFile

    pool = await get_pool()
    pending = await schedule_repo.get_pending_videos(pool, limit=3)

    if not pending:
        return

    for item in pending:
        sid = item["schedule_id"]
        logger.info("Scheduler: processing scheduled video %d: %s", sid, item["title"])

        await schedule_repo.update_schedule_status(pool, sid, "posting")

        try:
            title = item["title"]
            category = item["category"] or ""
            description = item["description"]
            file_url = item["file_url"]
            affiliate_link = item["affiliate_link"]
            thumbnail_b64 = item.get("thumbnail_b64")
            topic_ids_str = item.get("topic_ids") or ""

            is_telegram_file = not file_url.startswith(("http://", "https://"))

            # Generate video code and save to DB
            video = await video_repo.create_video(
                pool,
                title=title,
                category=category,
                description=description,
                file_url=file_url,
                affiliate_link=affiliate_link,
            )
            vid_id = video["video_id"]
            vid_code = video["code"]

            # Shorten URL if needed
            cdn_host = settings.bunny_cdn_hostname or ""
            is_cdn_url = cdn_host and file_url.startswith(cdn_host)
            if not is_telegram_file and not is_cdn_url:
                short = await shorten_url(file_url)
                if short:
                    await video_repo.set_shortened_url(pool, vid_id, short)

            # Build caption
            caption_lines = [f"<b>{title}</b>"]
            caption_lines.append(f"Code: <code>{vid_code}</code>")
            if description:
                caption_lines.append(f"\n{description}")
            caption_lines.append(f"\nCategory: {category}")
            caption = "\n".join(caption_lines)

            # Decode thumbnail
            thumbnail_data = base64.b64decode(thumbnail_b64) if thumbnail_b64 else None

            # If no thumbnail and it's a URL, try to extract one
            if not thumbnail_data and not is_telegram_file:
                url_to_extract = file_url
                if settings.bunny_cdn_hostname and settings.bunny_token_key and file_url.startswith(settings.bunny_cdn_hostname):
                    url_to_extract = sign_bunny_url(file_url, settings.bunny_cdn_hostname, settings.bunny_token_key)
                thumbnail_data = await extract_thumbnail(url_to_extract, timestamp_seconds=1)

            # Parse topic IDs
            topic_ids = [int(x.strip()) for x in topic_ids_str.split(",") if x.strip().isdigit()]

            # Post to each topic
            first_msg_id = None
            first_thread_id = None
            thumb_file_id = None

            for tid in topic_ids:
                topic = await topic_repo.get_topic_by_id(pool, tid)
                if not topic or not topic["thread_id"]:
                    continue
                thread_id = topic["thread_id"]

                msg_id, fid = await _post_to_topic_scheduled(
                    bot, thread_id, caption, file_url, is_telegram_file, vid_id,
                    thumbnail_data=thumbnail_data if not thumb_file_id else None,
                    thumbnail_file_id=thumb_file_id,
                )
                if fid and not thumb_file_id:
                    thumb_file_id = fid
                if msg_id and first_msg_id is None:
                    first_msg_id = msg_id
                    first_thread_id = thread_id

            # Post to "All" topic
            all_topic = await topic_repo.get_all_topic(pool)
            if all_topic and all_topic["thread_id"]:
                all_msg_id, fid = await _post_to_topic_scheduled(
                    bot, all_topic["thread_id"], caption, file_url, is_telegram_file, vid_id,
                    thumbnail_data=thumbnail_data if not thumb_file_id else None,
                    thumbnail_file_id=thumb_file_id,
                )
                if fid and not thumb_file_id:
                    thumb_file_id = fid

            # Update video record
            if first_msg_id:
                await video_repo.set_message_id(pool, vid_id, first_msg_id, first_thread_id)
            if thumb_file_id:
                await video_repo.set_thumbnail_file_id(pool, vid_id, thumb_file_id)

            await schedule_repo.update_schedule_status(pool, sid, "posted")
            logger.info("Scheduler: posted scheduled video %d (code %s)", sid, vid_code)

        except Exception as e:
            logger.exception("Scheduler: failed to post scheduled video %d", sid)
            await schedule_repo.update_schedule_status(pool, sid, "failed", error=str(e))


async def _post_to_topic_scheduled(
    bot: Bot,
    thread_id: int,
    caption: str,
    file_url: str,
    is_telegram_file: bool,
    video_id: int,
    thumbnail_data: bytes | None = None,
    thumbnail_file_id: str | None = None,
) -> tuple[int | None, str | None]:
    """Post a video to a specific forum topic (used by scheduler)."""
    from aiogram.types import BufferedInputFile
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

        msg = await bot.send_message(
            chat_id=settings.supergroup_id,
            message_thread_id=thread_id,
            text=caption,
            reply_markup=download_button(video_id),
        )
        return msg.message_id, None
    except Exception as e:
        logger.error("Failed to post scheduled video to thread %s: %s", thread_id, e)
        return None, None


async def start_scheduler(bot: Bot) -> None:
    """Run periodic tasks forever. Call this as a background asyncio task."""
    logger.info("Scheduler started (interval=%ds)", CHECK_INTERVAL)
    while True:
        try:
            await _check_newly_qualified(bot)
        except Exception:
            logger.exception("Scheduler error in check_newly_qualified")
        try:
            await _check_maintenance_auto_disable()
        except Exception:
            logger.exception("Scheduler error in check_maintenance_auto_disable")
        try:
            await _process_scheduled_videos(bot)
        except Exception:
            logger.exception("Scheduler error in process_scheduled_videos")
        await asyncio.sleep(CHECK_INTERVAL)
