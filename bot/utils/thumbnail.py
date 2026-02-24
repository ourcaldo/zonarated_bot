"""Thumbnail extraction from video URLs using ffmpeg."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to locate ffmpeg / ffprobe on the system
_FFMPEG_PATH: str | None = None
_FFPROBE_PATH: str | None = None


def _find_binary(name: str) -> str | None:
    """Locate an ffmpeg-family binary (ffmpeg or ffprobe)."""
    found = shutil.which(name)
    if found:
        return found

    # Check common winget install location (Windows)
    winget_dir = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    if winget_dir.exists():
        exe_name = f"{name}.exe"
        for pkg_dir in winget_dir.iterdir():
            if "FFmpeg" in pkg_dir.name:
                for exe in pkg_dir.rglob(exe_name):
                    return str(exe)
    return None


def _find_ffmpeg() -> str | None:
    global _FFMPEG_PATH
    if _FFMPEG_PATH is not None:
        return _FFMPEG_PATH
    _FFMPEG_PATH = _find_binary("ffmpeg")
    if not _FFMPEG_PATH:
        logger.warning("ffmpeg not found on this system")
    return _FFMPEG_PATH


def _find_ffprobe() -> str | None:
    global _FFPROBE_PATH
    if _FFPROBE_PATH is not None:
        return _FFPROBE_PATH
    _FFPROBE_PATH = _find_binary("ffprobe")
    if not _FFPROBE_PATH:
        logger.warning("ffprobe not found on this system")
    return _FFPROBE_PATH


async def _probe_video(video_url: str) -> dict:
    """Probe a video URL and return info about rotation and SAR.

    Returns dict with keys:
        has_rotation: bool  - True if rotation metadata or displaymatrix found
        has_non_square_sar: bool - True if SAR is not 1:1
    """
    result = {"has_rotation": False, "has_non_square_sar": False}

    ffprobe = _find_ffprobe()
    if not ffprobe:
        return result

    cmd = [
        ffprobe, "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        video_url,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)

        if proc.returncode != 0:
            return result

        data = json.loads(stdout.decode())

        for stream in data.get("streams", []):
            if stream.get("codec_type") != "video":
                continue

            # Check rotation in tags
            tags = stream.get("tags", {})
            rotation = tags.get("rotate") or tags.get("rotation")
            if rotation and rotation not in ("0", "0.0"):
                result["has_rotation"] = True
                logger.info("Probe: rotation metadata found (%s)", rotation)

            # Check displaymatrix in side_data_list
            for sd in stream.get("side_data_list", []):
                if "displaymatrix" in sd.get("side_data_type", "").lower():
                    rot = sd.get("rotation", 0)
                    if rot and float(rot) != 0:
                        result["has_rotation"] = True
                        logger.info("Probe: displaymatrix rotation found (%s)", rot)

            # Check SAR
            sar = stream.get("sample_aspect_ratio", "1:1")
            if sar and sar != "1:1" and sar != "0:1":
                parts = sar.split(":")
                if len(parts) == 2:
                    try:
                        num, den = int(parts[0]), int(parts[1])
                        if den > 0 and abs(num / den - 1.0) > 0.01:
                            result["has_non_square_sar"] = True
                            logger.info("Probe: non-square SAR found (%s)", sar)
                    except ValueError:
                        pass
            break  # only need the first video stream

    except asyncio.TimeoutError:
        logger.warning("ffprobe timed out for %s", video_url[:80])
    except Exception as e:
        logger.warning("ffprobe error: %s", e)

    return result


def _build_vf_filter(probe: dict) -> str:
    """Build the -vf filter string based on probe results.

    - Rotation metadata present: ffmpeg auto-rotates by default, just downscale.
    - Non-square SAR (no rotation): bake SAR into pixels, then downscale.
    - Normal video: just downscale.
    """
    if probe["has_non_square_sar"]:
        # Bake SAR into actual pixel dimensions, then cap width at 320
        return "scale=iw*sar:ih,scale='min(320,iw)':-2"
    else:
        # Auto-rotate handles rotation if present; just downscale
        return "scale='min(320,iw)':-2"


async def extract_thumbnail(
    video_url: str,
    timestamp_seconds: int = 1,
    quality: int = 2,
) -> bytes | None:
    """Extract a single frame from a video URL and return JPEG bytes.

    Probes the video first to detect orientation (rotation metadata vs
    non-square SAR) and applies the correct filter accordingly.

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

    # Probe video to determine orientation handling
    probe = await _probe_video(video_url)
    vf = _build_vf_filter(probe)
    logger.info("Thumbnail filter: %s (rotation=%s, sar=%s)",
                vf, probe["has_rotation"], probe["has_non_square_sar"])

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
            "-vf", vf,
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
