"""Entry point: python -m bot."""

from __future__ import annotations

import asyncio
import logging
import sys

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import bot.config as bot_config
from bot.config import settings
from bot.db.pool import create_pool, close_pool
from bot.handlers import register_routers
from bot.scheduler import start_scheduler
from bot.web import create_web_app, set_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

WEB_PORT = 8080


async def main() -> None:
    """Initialise DB pool, register handlers, start polling + web server."""
    logger.info("Starting Zona Rated Bot …")

    # Database
    pool = await create_pool()
    logger.info("Database pool ready")

    # Bot & Dispatcher
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Resolve bot username once at startup
    me = await bot.get_me()
    bot_config.bot_username = me.username
    logger.info("Bot username: @%s", me.username)

    # Register all routers
    register_routers(dp)

    # Share bot instance with web server
    set_bot(bot)

    # Start aiohttp web server
    app = create_web_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEB_PORT)
    await site.start()
    logger.info("Web server started on port %s", WEB_PORT)

    try:
        # Drop pending updates so we don't replay old ones
        await bot.delete_webhook(drop_pending_updates=True)

        # Start background scheduler (cron jobs)
        scheduler_task = asyncio.create_task(start_scheduler(bot))

        logger.info("Polling started")
        await dp.start_polling(bot)
    finally:
        logger.info("Shutting down …")
        scheduler_task.cancel()
        await runner.cleanup()
        await close_pool()
        await bot.session.close()
        logger.info("Bye!")


if __name__ == "__main__":
    asyncio.run(main())
