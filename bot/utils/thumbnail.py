"""Thumbnail extraction from video URLs using ffmpeg."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to locate ffmpeg on the system
_FFMPEG_PATH: str | None = None


def _find_ffmpeg() -> str | None:
    """Locate the ffmpeg binary. Checks PATH first, then winget install dir."""
    global _FFMPEG_PATH
    if _FFMPEG_PATH is not None:
        return _FFMPEG_PATH

    # Check if ffmpeg is on PATH
    found = shutil.which("ffmpeg")
    if found:
        _FFMPEG_PATH = found
        return _FFMPEG_PATH

    # Check common winget install location (Windows)
    winget_dir = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    if winget_dir.exists():
        for pkg_dir in winget_dir.iterdir():
            if "FFmpeg" in pkg_dir.name:
                for exe in pkg_dir.rglob("ffmpeg.exe"):
                    _FFMPEG_PATH = str(exe)
                    return _FFMPEG_PATH

    logger.warning("ffmpeg not found on this system")
    return None


async def extract_thumbnail(
    video_url: str,
    timestamp_seconds: int = 1,
    quality: int = 2,
) -> bytes | None:
    """Extract a single frame from a video URL and return JPEG bytes.

    Args:
        video_url: HTTP(S) URL of the video.
        timestamp_seconds: Which second to grab the frame from (default 1).
        quality: JPEG quality (2 = high, 31 = low). Default 2.

    Returns:
        JPEG image bytes, or None if extraction failed.
    """
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        logger.error("Cannot extract thumbnail: ffmpeg not found")
        return None

    # Use a temp file for the output
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
    os.close(tmp_fd)

    try:
        ts = f"00:00:{timestamp_seconds:02d}" if timestamp_seconds < 60 else str(timestamp_seconds)

        cmd = [
            ffmpeg, "-y",
            "-ss", ts,
            "-i", video_url,
            "-frames:v", "1",
            "-q:v", str(quality),
            "-vf", "scale='min(320,iw)':-2",
            "-update", "1",
            tmp_path,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if proc.returncode != 0:
            logger.error("ffmpeg failed (code %s): %s", proc.returncode, stderr.decode()[-500:])
            return None

        thumb_path = Path(tmp_path)
        if not thumb_path.exists() or thumb_path.stat().st_size == 0:
            logger.error("ffmpeg produced empty or missing thumbnail")
            return None

        data = thumb_path.read_bytes()
        logger.info(
            "Thumbnail extracted: %d bytes, ts=%ds, url=%s",
            len(data), timestamp_seconds, video_url[:80],
        )
        return data

    except asyncio.TimeoutError:
        logger.error("ffmpeg timed out after 30s for %s", video_url[:80])
        return None
    except Exception as e:
        logger.error("Thumbnail extraction error: %s", e)
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
