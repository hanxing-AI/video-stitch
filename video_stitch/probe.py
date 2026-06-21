"""ffprobe wrapper for video metadata extraction."""

import json
import subprocess
import logging
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger("video_stitch")


@dataclass
class VideoStream:
    """Metadata for a single video stream."""
    index: int
    codec: str
    width: int
    height: int
    fps: float
    pix_fmt: str = "unknown"
    duration: float = 0.0
    bitrate: int = 0


@dataclass
class AudioStream:
    """Metadata for a single audio stream."""
    index: int
    codec: str
    sample_rate: int = 0
    channels: int = 0
    channel_layout: str = "unknown"
    duration: float = 0.0
    bitrate: int = 0


@dataclass
class FileInfo:
    """Complete metadata for a media file."""
    path: str
    format_name: str = "unknown"
    duration: float = 0.0
    size_bytes: int = 0
    video: List[VideoStream] = field(default_factory=list)
    audio: List[AudioStream] = field(default_factory=list)

    @property
    def has_video(self) -> bool:
        return len(self.video) > 0

    @property
    def has_audio(self) -> bool:
        return len(self.audio) > 0

    @property
    def primary_video(self) -> Optional[VideoStream]:
        return self.video[0] if self.video else None

    @property
    def primary_audio(self) -> Optional[AudioStream]:
        return self.audio[0] if self.audio else None


def probe(filepath: str) -> FileInfo:
    """Extract complete metadata from a media file using ffprobe.

    Args:
        filepath: Path to the media file.

    Returns:
        FileInfo with all available metadata.

    Raises:
        FileNotFoundError: If filepath doesn't exist.
        RuntimeError: If ffprobe fails or returns unparseable output.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"ffprobe failed on '{filepath}': {e.stderr.strip()}"
        ) from e
    except FileNotFoundError:
        raise RuntimeError(
            "ffprobe not found. Please install ffmpeg (which includes ffprobe)."
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Failed to parse ffprobe output for '{filepath}': {e}"
        ) from e

    return _parse_probe_output(data, str(path))


def probe_json(filepath: str) -> str:
    """Return raw ffprobe JSON output as a string.

    Useful for debugging or piping to other tools.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def probe_summary(filepath: str) -> str:
    """Return a human-readable one-line summary of a media file.

    Example: "clip.mp4: 1920x1080@30fps h264, aac 48000Hz stereo, duration 2:30.500"
    """
    info = probe(filepath)

    parts = [f"{Path(filepath).name}:"]

    if info.primary_video:
        v = info.primary_video
        parts.append(f" {v.width}x{v.height}@{v.fps:.0f}fps {v.codec}")

    if info.primary_audio:
        a = info.primary_audio
        layout = a.channel_layout if a.channel_layout != "unknown" else f"{a.channels}ch"
        parts.append(f", {a.codec} {a.sample_rate}Hz {layout}")

    from .utils import format_duration
    parts.append(f", duration {format_duration(info.duration)}")

    return "".join(parts)


def compatible(a: FileInfo, b: FileInfo) -> bool:
    """Check if two files have compatible video streams (same res, fps, pix_fmt)."""
    av = a.primary_video
    bv = b.primary_video
    if not av or not bv:
        return False
    return (
        av.width == bv.width and
        av.height == bv.height and
        abs(av.fps - bv.fps) < 0.01 and
        av.pix_fmt == bv.pix_fmt
    )


def find_common_params(files: List[FileInfo]) -> dict:
    """Find consensus video parameters from a list of files.

    Uses the most common resolution and highest FPS among inputs.
    Falls back to defaults if no video streams found.

    Returns:
        dict with keys: width, height, fps, pix_fmt
    """
    if not files:
        from .constants import DEFAULT_RESOLUTION, DEFAULT_FPS, DEFAULT_PIX_FMT
        return {
            "width": DEFAULT_RESOLUTION[0],
            "height": DEFAULT_RESOLUTION[1],
            "fps": DEFAULT_FPS,
            "pix_fmt": DEFAULT_PIX_FMT,
        }

    from collections import Counter
    from .constants import DEFAULT_RESOLUTION, DEFAULT_FPS, DEFAULT_PIX_FMT

    resolutions = []
    fpss = []
    pix_fmts = []

    for f in files:
        if f.primary_video:
            resolutions.append((f.primary_video.width, f.primary_video.height))
            fpss.append(f.primary_video.fps)
            pix_fmts.append(f.primary_video.pix_fmt)

    if not resolutions:
        return {
            "width": DEFAULT_RESOLUTION[0],
            "height": DEFAULT_RESOLUTION[1],
            "fps": DEFAULT_FPS,
            "pix_fmt": DEFAULT_PIX_FMT,
        }

    # Most common resolution
    res_counter = Counter(resolutions)
    width, height = res_counter.most_common(1)[0][0]

    # Most common FPS (rounded to 2 decimals to group similar rates)
    fps_counter = Counter(round(f, 2) for f in fpss)
    fps = fps_counter.most_common(1)[0][0]

    # Most common pixel format
    fmt_counter = Counter(pix_fmts)
    pix_fmt = fmt_counter.most_common(1)[0][0]

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "pix_fmt": pix_fmt,
    }


def _parse_probe_output(data: dict, filepath: str) -> FileInfo:
    """Parse ffprobe JSON output into FileInfo dataclass."""
    info = FileInfo(path=filepath)

    fmt = data.get("format", {})
    info.format_name = fmt.get("format_name", "unknown")
    info.duration = float(fmt.get("duration", 0))
    info.size_bytes = int(fmt.get("size", 0))

    for stream in data.get("streams", []):
        codec_type = stream.get("codec_type", "")

        if codec_type == "video":
            fps = _parse_fps(stream)
            vs = VideoStream(
                index=stream.get("index", 0),
                codec=stream.get("codec_name", "unknown"),
                width=stream.get("width", 0),
                height=stream.get("height", 0),
                fps=fps,
                pix_fmt=stream.get("pix_fmt", "unknown"),
                duration=float(stream.get("duration",
                                fmt.get("duration", 0))),
                bitrate=int(stream.get("bit_rate", 0)),
            )
            info.video.append(vs)

        elif codec_type == "audio":
            ch_layout = stream.get("channel_layout", "")
            if not ch_layout:
                channels = stream.get("channels", 0)
                ch_layout = _channel_layout_name(channels)

            astr = AudioStream(
                index=stream.get("index", 0),
                codec=stream.get("codec_name", "unknown"),
                sample_rate=int(stream.get("sample_rate", 0)),
                channels=stream.get("channels", 0),
                channel_layout=ch_layout,
                duration=float(stream.get("duration",
                                fmt.get("duration", 0))),
                bitrate=int(stream.get("bit_rate", 0)),
            )
            info.audio.append(astr)

    # If stream durations are 0, use format duration
    if info.duration == 0:
        info.duration = float(fmt.get("duration", 0))

    return info


def _parse_fps(stream: dict) -> float:
    """Parse framerate from ffprobe stream data.

    r_frame_rate is like "30000/1001" or "30/1".
    avg_frame_rate is the average actual framerate.
    We use r_frame_rate as it's the "real" framerate.
    """
    rfr = stream.get("r_frame_rate", "0/1")
    if "/" in rfr:
        num, den = rfr.split("/", 1)
        try:
            if int(den) != 0:
                return float(num) / float(den)
        except (ValueError, ZeroDivisionError):
            pass

    # Fallback to avg_frame_rate
    afr = stream.get("avg_frame_rate", "0/1")
    if "/" in afr:
        num, den = afr.split("/", 1)
        try:
            if int(den) != 0:
                return float(num) / float(den)
        except (ValueError, ZeroDivisionError):
            pass

    return 0.0


def _channel_layout_name(channels: int) -> str:
    """Map channel count to common layout names."""
    mapping = {
        0: "unknown",
        1: "mono",
        2: "stereo",
        3: "2.1",
        4: "4.0",
        5: "5.0",
        6: "5.1",
        7: "6.1",
        8: "7.1",
    }
    return mapping.get(channels, f"{channels}ch")
