"""Video trimming — cut segments with start/end times."""

import logging
from dataclasses import dataclass
from typing import Optional

from .pipeline import FFmpegCommand
from .utils import parse_time

logger = logging.getLogger("video_stitch")


@dataclass
class TrimSpec:
    """Specification for trimming a video segment.

    start: Start time in seconds.
    end: End time in seconds (None = to the end of the video).
    duration: Alternative to end — trim this many seconds from start.
    """
    start: float = 0.0
    end: Optional[float] = None
    duration: Optional[float] = None

    def validate(self, total_duration: float = float("inf")) -> list:
        """Validate trim spec against total video duration.

        Returns:
            List of error strings (empty = valid).
        """
        errors = []
        if self.start < 0:
            errors.append(f"Trim start cannot be negative: {self.start}")
        if self.start >= total_duration:
            errors.append(
                f"Trim start ({self.start}s) is beyond video duration "
                f"({total_duration}s)"
            )
        if self.end is not None and self.end <= self.start:
            errors.append(
                f"Trim end ({self.end}s) must be after start ({self.start}s)"
            )
        if self.duration is not None and self.duration <= 0:
            errors.append(
                f"Trim duration must be positive: {self.duration}"
            )
        return errors

    @property
    def effective_duration(self) -> Optional[float]:
        """Compute the effective duration of the trimmed segment."""
        if self.duration is not None:
            return self.duration
        if self.end is not None:
            return self.end - self.start
        return None  # To the end


def parse_trim(spec: str) -> TrimSpec:
    """Parse a trim specification string.

    Formats supported:
        "5.0-30.0"  -> TrimSpec(5.0, 30.0)
        "10-"       -> TrimSpec(10.0, None)  (from 10s to end)
        "-20"       -> TrimSpec(0.0, 20.0)
        "15"        -> TrimSpec(0.0, duration=15)

    Args:
        spec: Trim specification string.

    Returns:
        TrimSpec object.

    Raises:
        ValueError: If the spec cannot be parsed.
    """
    spec = spec.strip()

    if "-" in spec:
        parts = spec.split("-", 1)
        left = parts[0].strip()
        right = parts[1].strip()

        if left and right:
            # "5.0-30.0"
            return TrimSpec(
                start=parse_time(left),
                end=parse_time(right),
            )
        elif left and not right:
            # "10-"
            return TrimSpec(start=parse_time(left), end=None)
        elif not left and right:
            # "-20"
            return TrimSpec(start=0.0, end=parse_time(right))
        else:
            # "-" (just a dash)
            raise ValueError(f"Invalid trim spec: '{spec}'")
    else:
        # "15" — treat as trim from 0 to duration=15
        return TrimSpec(start=0.0, duration=parse_time(spec))


def apply_trim(input_path: str, output_path: str, trim: TrimSpec,
               total_duration: float = float("inf"),
               dry_run: bool = False) -> str:
    """Trim a video file to the specified segment.

    Uses fast seek (-ss before -i) for the start, and -t or -to for the end.
    Also resets timestamps so output starts at 0:00.

    Args:
        input_path: Path to the source video.
        output_path: Where to write the trimmed file.
        trim: TrimSpec describing the segment to extract.
        total_duration: Known video duration for validation.
        dry_run: If True, print command without executing.

    Returns:
        output_path on success.

    Raises:
        subprocess.CalledProcessError: If ffmpeg fails.
    """
    errors = trim.validate(total_duration)
    if errors:
        raise ValueError(f"Invalid trim for '{input_path}': " + "; ".join(errors))

    cmd = FFmpegCommand()
    cmd.set_boolean("y")

    # Fast seek: -ss before -i for speed (may be slightly inaccurate
    # but good enough for non-professional use)
    input_opts = {}
    if trim.start > 0:
        input_opts["ss"] = f"{trim.start:.3f}"

    cmd.add_input(input_path, **input_opts)

    # Determine output duration/stop
    output_opts = {
        "c:v": "libx264",
        "c:a": "aac",
        "preset": "ultrafast",
        "crf": "18",
        "pix_fmt": "yuv420p",
        "movflags": "+faststart",
    }

    # Reset timestamps
    output_opts["vf"] = "setpts=PTS-STARTPTS"
    output_opts["af"] = "asetpts=PTS-STARTPTS"

    if trim.duration is not None:
        output_opts["t"] = f"{trim.duration:.3f}"
    elif trim.end is not None:
        # Use -t (duration) instead of -to for reliable behavior
        # with -ss before -i (fast seek)
        dur = trim.end - trim.start
        output_opts["t"] = f"{dur:.3f}"

    cmd.add_output(output_path, **output_opts)

    cmd.run(dry_run=dry_run, verbose=True)
    logger.info(
        f"Trimmed: {input_path} [{trim.start:.1f}s"
        f"{f' - {trim.end:.1f}s' if trim.end else ''}]"
        f" -> {output_path}"
    )
    return output_path
