"""Entry point: python -m bot."""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import settings
from bot.db.pool import create_pool, close_pool
from bot.handlers import register_routers
from bot.scheduler import start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Initialise DB pool, register handlers, start polling."""
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

    # Register all routers
    register_routers(dp)

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
        await close_pool()
        await bot.session.close()
        logger.info("Bye!")


if __name__ == "__main__":
    asyncio.run(main())
