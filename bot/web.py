"""Lightweight aiohttp web server for verified redirect tracking.

Runs alongside the Telegram bot in the same process.
Single route: GET /{token} — validates download session,
marks it as visited, triggers auto-delivery, and redirects
the user's browser to the affiliate/ShrinkMe URL.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiohttp import web

from bot.db.pool import get_pool
from bot.db import config_repo, video_repo, user_repo

logger = logging.getLogger(__name__)

# Stored reference to the Bot instance (set from run.py)
_bot = None


def set_bot(bot) -> None:
    """Store the Bot instance so the web handler can use it."""
    global _bot
    _bot = bot


async def handle_redirect(request: web.Request) -> web.Response:
    """Handle GET /{token} — verify visit, deliver video, redirect."""
    token = request.match_info.get("token", "")
    if not token:
        return web.Response(text="Invalid link.", status=400)

    pool = await get_pool()
    session = await video_repo.get_download_session(pool, token)

    if not session:
        return web.Response(
            text="Link expired or invalid.",
            status=404,
            content_type="text/html",
        )

    # Check expiry
    if session["expires_at"]:
        expires = session["expires_at"]
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            return web.Response(
                text="Link expired. Please request a new download from the bot.",
                status=410,
                content_type="text/html",
            )

    # Check if already visited (single-use)
    if session.get("visited_at") is not None:
        return web.Response(
            text="This link has already been used.",
            status=410,
            content_type="text/html",
        )

    # Check if video already sent
    if session["video_sent"]:
        return web.Response(
            text="Video already delivered. Check your Telegram chat.",
            status=410,
            content_type="text/html",
        )

    user_id = session["user_id"]
    video_id = session["video_id"]

    # Mark visited
    await video_repo.mark_visited(pool, token)
    await video_repo.mark_affiliate_visited(pool, token)

    # Get video info
    video = await video_repo.get_video(pool, video_id)
    if not video:
        return web.Response(text="Video not found.", status=404)

    # Auto-deliver video to user's Telegram chat
    if _bot is not None:
        try:
            user = await user_repo.get_user(pool, user_id)
            lang = (user["language"] if user else None) or "id"

            from bot.handlers.video import _deliver_video
            await _deliver_video(_bot, user_id, video, lang)

            # Update session and stats
            await video_repo.mark_video_sent(pool, token)
            await video_repo.increment_downloads(pool, video_id)
            await video_repo.log_download(pool, user_id, video_id, token, True)

            logger.info("Auto-delivered video %s to user %s via redirect", video_id, user_id)
        except Exception as e:
            logger.error("Failed to auto-deliver video %s to user %s: %s", video_id, user_id, e)
    else:
        logger.warning("Bot instance not set, skipping video delivery for session %s", token)

    # Determine redirect target — affiliate/ShrinkMe URL
    redirect_url = video.get("affiliate_link")
    if not redirect_url:
        redirect_url = await config_repo.get_affiliate_link(pool)
    if not redirect_url:
        # Fallback: shortened URL or raw file URL
        redirect_url = video.get("shortened_url") or video.get("file_url") or "https://t.me/zonarated_bot"

    # 302 redirect to the affiliate page
    raise web.HTTPFound(redirect_url)


def create_web_app() -> web.Application:
    """Create the aiohttp web application."""
    app = web.Application()
    app.router.add_get("/{token}", handle_redirect)
    return app
