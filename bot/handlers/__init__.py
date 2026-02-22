"""Register all handler routers."""

from aiogram import Router

from bot.handlers.start import router as start_router
from bot.handlers.join import router as join_router
from bot.handlers.join_request import router as join_request_router
from bot.handlers.admin import router as admin_router
from bot.handlers.video import router as video_router
from bot.handlers.common import router as common_router


def register_routers(parent: Router) -> None:
    """Attach all child routers to the given parent (usually the Dispatcher)."""
    parent.include_router(start_router)
    parent.include_router(join_router)
    parent.include_router(join_request_router)
    parent.include_router(admin_router)
    parent.include_router(video_router)
    parent.include_router(common_router)
