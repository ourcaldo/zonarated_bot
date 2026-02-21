"""Bot package configuration — loads .env into typed settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


def _require(key: str) -> str:
    """Return env var or raise with a clear message."""
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    supergroup_id: int
    database_url: str


settings = Settings(
    bot_token=_require("BOT_TOKEN"),
    supergroup_id=int(_require("SUPERGROUP_ID")),
    database_url=_require("DATABASE_URL"),
)
