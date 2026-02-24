"""Bunny Edge Storage API client — list video files from the CDN storage.

Uses the Bunny Storage HTTP API:
    GET https://{region}.storage.bunnycdn.com/{zone}/{path}/
    Headers: AccessKey: {api_key}

Storage structure:
    /{zone}/
        Asia/
            video1.mp4
            video2.mkv
            Model X/
                video3.mp4
                image.jpg (ignored)
            Model Y/
                video4.avi
        Western/
            ...
        Solo/
            ...

Category = top-level folder (matches DB topic name).
Sub-folders are recursively scanned but do NOT represent categories.
Only video files (by extension) are collected.
"""

from __future__ import annotations

import logging
from urllib.parse import quote

import aiohttp

from bot.db.pool import get_pool
from bot.db import config_repo

logger = logging.getLogger(__name__)

# Video file extensions (lowercase, with dot)
_VIDEO_EXTENSIONS = frozenset({
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv",
    ".flv", ".m4v", ".mpg", ".mpeg", ".3gp", ".ts",
})


async def _get_credentials() -> tuple[str, str, str]:
    """Read storage credentials from config table."""
    pool = await get_pool()
    api_key = await config_repo.get_config(pool, "BUNNY_STORAGE_API_KEY") or ""
    zone = await config_repo.get_config(pool, "BUNNY_STORAGE_ZONE") or ""
    region = await config_repo.get_config(pool, "BUNNY_STORAGE_REGION") or ""
    return api_key, zone, region


def _build_base_url(region: str) -> str:
    """Build the storage API base URL from region code."""
    if region:
        return f"https://{region}.storage.bunnycdn.com"
    return "https://storage.bunnycdn.com"


def _is_video_file(name: str) -> bool:
    """Check if a filename has a video extension."""
    dot = name.rfind(".")
    if dot == -1:
        return False
    ext = name[dot:].lower()
    return ext in _VIDEO_EXTENSIONS


def _title_from_filename(name: str) -> str:
    """Generate a human-readable title from a filename.

    'my_cool_video.mp4' -> 'My Cool Video'
    """
    dot = name.rfind(".")
    if dot != -1:
        name = name[:dot]
    # Replace common separators with spaces
    for ch in "_-":
        name = name.replace(ch, " ")
    return name.strip().title()


async def _list_path(api_key: str, base_url: str, zone: str, path: str) -> list[dict]:
    """List objects at a given storage path. Returns raw Bunny API objects."""
    # Ensure path ends with /
    if not path.endswith("/"):
        path += "/"

    url = f"{base_url}/{zone}/{path}"

    headers = {"AccessKey": api_key, "Accept": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Bunny Storage API error {resp.status}: {text[:200]}")
            return await resp.json()


async def _collect_videos_recursive(
    api_key: str,
    base_url: str,
    zone: str,
    path: str,
    cdn_hostname: str,
) -> list[dict]:
    """Recursively collect all video files under a path.

    Returns list of dicts: {"url": cdn_url, "title": generated_title, "path": storage_path}
    """
    results = []

    try:
        objects = await _list_path(api_key, base_url, zone, path)
    except Exception as e:
        logger.warning("Failed to list path '%s': %s", path, e)
        return results

    for obj in objects:
        name = obj.get("ObjectName", "")
        is_dir = obj.get("IsDirectory", False)

        if is_dir:
            sub_path = f"{path}{name}/"
            sub_results = await _collect_videos_recursive(
                api_key, base_url, zone, sub_path, cdn_hostname
            )
            results.extend(sub_results)
        else:
            if _is_video_file(name):
                # Build CDN URL
                file_path = f"{path}{name}"
                # URL-encode the file path for the CDN URL
                encoded_path = "/".join(quote(segment, safe="") for segment in file_path.split("/"))
                cdn_url = f"{cdn_hostname}/{encoded_path}"

                results.append({
                    "url": cdn_url,
                    "title": _title_from_filename(name),
                    "path": file_path,
                    "filename": name,
                })

    return results


async def list_category_videos(category_name: str) -> list[dict]:
    """List all video files in a category folder (recursively).

    Args:
        category_name: The category/topic name, which must match the
                       top-level folder name in Bunny Storage.

    Returns:
        List of dicts with keys: url, title, path, filename
    """
    api_key, zone, region = await _get_credentials()

    if not api_key or not zone:
        raise RuntimeError(
            "Bunny Storage not configured. Set BUNNY_STORAGE_API_KEY and BUNNY_STORAGE_ZONE in settings."
        )

    base_url = _build_base_url(region)

    # Get the CDN hostname from settings
    from bot.config import settings
    cdn_hostname = settings.bunny_cdn_hostname
    if not cdn_hostname:
        raise RuntimeError("BUNNY_CDN_HOSTNAME not configured in .env")

    # Remove trailing slash from CDN hostname
    cdn_hostname = cdn_hostname.rstrip("/")

    # Scan the category folder
    path = f"{category_name}/"
    return await _collect_videos_recursive(api_key, base_url, zone, path, cdn_hostname)


async def list_all_categories() -> list[str]:
    """List top-level folders (categories) in the storage zone."""
    api_key, zone, region = await _get_credentials()
    if not api_key or not zone:
        return []

    base_url = _build_base_url(region)

    try:
        objects = await _list_path(api_key, base_url, zone, "/")
    except Exception as e:
        logger.warning("Failed to list root: %s", e)
        return []

    return [obj["ObjectName"] for obj in objects if obj.get("IsDirectory")]


async def resolve_storage_folder(topic_name: str) -> str | None:
    """Match a DB topic name to an actual Bunny Storage folder.

    Topic names may use the format 'Local / English' (e.g. 'Solo / Solo',
    'Barat / Western').  Storage folders use a single word (e.g. 'Solo',
    'Western').  This function lists the root folders and returns the first
    one that matches any segment of the topic name (case-insensitive).

    Returns the exact folder name from storage, or None if no match.
    """
    folders = await list_all_categories()
    if not folders:
        return None

    # Split topic name on ' / ' and also try the full name
    candidates = [s.strip() for s in topic_name.split("/")]
    candidates.append(topic_name.strip())

    folder_lower = {f.lower(): f for f in folders}

    for candidate in candidates:
        match = folder_lower.get(candidate.lower())
        if match:
            return match

    return None
