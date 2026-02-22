"""URL shortener integration using ShrinkMe.io API."""

from __future__ import annotations

import logging
import urllib.parse

import aiohttp

from bot.db.pool import get_pool
from bot.db import config_repo

logger = logging.getLogger(__name__)

_API_BASE = "https://shrinkme.io/api"


async def shorten_url(long_url: str) -> str | None:
    """Shorten a URL using ShrinkMe.io.

    Reads the API key from the config table (SHRINKME_API_KEY).
    Returns the shortened URL, or None if the API call fails
    or no API key is configured.
    """
    pool = await get_pool()
    api_key = await config_repo.get_shrinkme_api_key(pool)
    if not api_key:
        logger.warning("ShrinkMe API key not configured, skipping URL shortening")
        return None

    encoded_url = urllib.parse.quote(long_url, safe="")
    request_url = f"{_API_BASE}?api={api_key}&url={encoded_url}&format=text"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(request_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.error("ShrinkMe API returned status %s", resp.status)
                    return None
                text = (await resp.text()).strip()
                if text and text.startswith("http"):
                    logger.info("URL shortened: %s -> %s", long_url[:60], text)
                    return text
                logger.error("ShrinkMe API returned unexpected response: %s", text[:200])
                return None
    except Exception as e:
        logger.error("ShrinkMe API error: %s", e)
        return None
