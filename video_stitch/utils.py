"""Pure utility functions: temp files, time parsing, path helpers."""

import os
import re
import shutil
import tempfile
import subprocess
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger("video_stitch")


def parse_time(time_str: str) -> float:
    """Parse time strings to float seconds.

    Supports formats:
        "90"     -> 90.0 seconds
        "1:30"   -> 90.0 seconds (MM:SS)
        "1:30.5" -> 90.5 seconds (MM:SS.ms)
        "1.5"    -> 1.5 seconds
        "1:02:30" -> 3750.0 seconds (HH:MM:SS)

    Returns float seconds.
    Raises ValueError for unparseable input.
    """
    time_str = time_str.strip()
    if not time_str:
        raise ValueError("Empty time string")

    # HH:MM:SS or HH:MM:SS.ms
    if time_str.count(":") == 2:
        parts = time_str.split(":")
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds

    # MM:SS or MM:SS.ms
    if time_str.count(":") == 1:
        parts = time_str.split(":")
        minutes = int(parts[0])
        seconds = float(parts[1])
        return minutes * 60 + seconds

    # Plain seconds (possibly fractional)
    return float(time_str)


def format_duration(seconds: float) -> str:
    """Format float seconds to MM:SS.ms string."""
    if seconds < 0:
        seconds = 0.0
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:06.3f}"
    return f"{minutes}:{secs:06.3f}"


def estimate_file_size(duration: float, width: int, height: int,
                       fps: float = 30, bitrate_mbps: float = 5.0) -> int:
    """Estimate output file size in bytes (rough approximation)."""
    # Very rough: bitrate * duration + 10% overhead
    size_bits = bitrate_mbps * 1_000_000 * duration * 1.1
    return int(size_bits / 8)


@contextmanager
def temp_dir(prefix: str = "video-stitch-", keep: bool = False):
    """Context manager for a temporary directory.

    Args:
        prefix: Directory name prefix.
        keep: If True, do not delete the directory on exit.

    Yields:
        Path to the temporary directory.
    """
    tmp = tempfile.mkdtemp(prefix=prefix)
    try:
        yield tmp
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            logger.info(f"Temporary files kept at: {tmp}")


def temp_filename(prefix: str, ext: str, directory: str) -> str:
    """Generate a unique temp filename in the given directory.

    Args:
        prefix: Filename prefix (e.g., "normalized").
        ext: File extension WITHOUT dot (e.g., "mp4").
        directory: Directory to place the file in.

    Returns:
        Full path to the new temp file.
    """
    fd, path = tempfile.mkstemp(prefix=f"{prefix}_", suffix=f".{ext}",
                                dir=directory)
    os.close(fd)
    return path


def ensure_dir(path: str) -> str:
    """Create directory if it doesn't exist, return path."""
    os.makedirs(path, exist_ok=True)
    return path


def which(program: str) -> Optional[str]:
    """Find the full path to an executable, or None."""
    return shutil.which(program)


def require_program(program: str) -> str:
    """Find program path or raise RuntimeError with helpful message."""
    path = which(program)
    if path is None:
        raise RuntimeError(
            f"Required program '{program}' not found in PATH.\n"
            f"Please install {program} and try again."
        )
    return path


def run_ffmpeg(args: List[str], dry_run: bool = False,
               capture: bool = True) -> subprocess.CompletedProcess:
    """Run an ffmpeg command with consistent error handling.

    Args:
        args: ffmpeg argument list (including 'ffmpeg' as first element).
        dry_run: If True, print command and return without executing.
        capture: If True, capture stdout/stderr.

    Returns:
        subprocess.CompletedProcess.

    Raises:
        subprocess.CalledProcessError: If ffmpeg exits non-zero.
    """
    cmd_str = " ".join(args)
    if dry_run:
        logger.info(f"[DRY RUN] {cmd_str}")
        return subprocess.CompletedProcess(args, 0, stdout=b"", stderr=b"")

    logger.debug(f"Running: {cmd_str}")
    try:
        result = subprocess.run(
            args,
            capture_output=capture,
            text=True,
            check=True,
        )
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg failed with code {e.returncode}")
        if e.stderr:
            # Print last 10 lines of stderr for diagnosis
            stderr_lines = e.stderr.strip().split("\n")
            relevant = stderr_lines[-10:]
            logger.error("ffmpeg stderr (last 10 lines):\n" + "\n".join(relevant))
        raise


def run_ffprobe(args: List[str]) -> dict:
    """Run ffprobe and return parsed JSON output.

    Args:
        args: ffprobe arguments including 'ffprobe' as first element.
              Should include '-print_format json' or equivalent.

    Returns:
        Parsed JSON dict.
    """
    import json
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def normalize_path(path: str) -> str:
    """Normalize a file path: resolve home dir, use forward slashes."""
    expanded = os.path.expanduser(path)
    # Use forward slashes (ffmpeg on Windows handles them fine)
    normalized = expanded.replace("\\", "/")
    return normalized
