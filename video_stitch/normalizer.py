"""Video normalization module.

Ensures all input files share the same resolution, framerate,
pixel format, and audio parameters before stitching.

Uses letterbox/pillarbox (pad) to preserve aspect ratio —
no stretching, no cropping. The safe default for non-professionals.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from .probe import FileInfo, probe
from .pipeline import FFmpegCommand
from .constants import (
    DEFAULT_RESOLUTION, DEFAULT_FPS, DEFAULT_VIDEO_CODEC,
    DEFAULT_PIX_FMT, DEFAULT_AUDIO_CODEC, DEFAULT_AUDIO_BITRATE,
    DEFAULT_SAMPLE_RATE, DEFAULT_CHANNEL_LAYOUT,
    INTERMEDIATE_CRF, INTERMEDIATE_PRESET,
)

logger = logging.getLogger("video_stitch")


@dataclass
class NormalizeConfig:
    """Configuration for video/audio normalization."""
    width: int = DEFAULT_RESOLUTION[0]
    height: int = DEFAULT_RESOLUTION[1]
    fps: float = DEFAULT_FPS
    pix_fmt: str = DEFAULT_PIX_FMT
    video_codec: str = DEFAULT_VIDEO_CODEC
    audio_codec: str = DEFAULT_AUDIO_CODEC
    audio_bitrate: str = DEFAULT_AUDIO_BITRATE
    sample_rate: int = DEFAULT_SAMPLE_RATE
    channel_layout: str = DEFAULT_CHANNEL_LAYOUT
    crf: int = INTERMEDIATE_CRF
    preset: str = INTERMEDIATE_PRESET


def normalize(input_path: str, output_path: str,
              config: Optional[NormalizeConfig] = None,
              dry_run: bool = False) -> str:
    """Normalize a single video file to the target configuration.

    Preserves aspect ratio by scaling down to fit within target dimensions,
    then padding with black bars (letterbox/pillarbox) to fill exactly.

    Args:
        input_path: Path to the source video.
        output_path: Where to write the normalized file.
        config: Normalization parameters (uses defaults if None).
        dry_run: If True, print commands without executing.

    Returns:
        output_path on success.

    Raises:
        subprocess.CalledProcessError: If ffmpeg fails.
    """
    if config is None:
        config = NormalizeConfig()

    # Build the video filter chain
    # scale: fit within WxH, preserving aspect ratio
    # pad: fill to exactly WxH with black bars centered
    # fps: set target framerate
    # settb + setpts: normalize timestamps
    # format: set pixel format
    vf_parts = [
        f"scale={config.width}:{config.height}:force_original_aspect_ratio=decrease",
        f"pad={config.width}:{config.height}:(ow-iw)/2:(oh-ih)/2",
        f"fps={config.fps}",
        "settb=AVTB",
        "setpts=PTS-STARTPTS",
        f"format={config.pix_fmt}",
    ]
    vf_filter = ",".join(vf_parts)

    # Build the audio filter chain
    af_parts = [
        f"aformat=sample_rates={config.sample_rate}:"
        f"channel_layouts={config.channel_layout}",
        "asetpts=PTS-STARTPTS",
    ]
    af_filter = ",".join(af_parts)

    cmd = FFmpegCommand()
    cmd.set_boolean("y")
    cmd.add_input(input_path)
    cmd.add_output(
        output_path,
        **{
            "c:v": config.video_codec,
            "preset": config.preset,
            "crf": str(config.crf),
            "pix_fmt": config.pix_fmt,
            "c:a": config.audio_codec,
            "b:a": config.audio_bitrate,
            "ar": str(config.sample_rate),
            "ac": "2",  # stereo
            "vf": vf_filter,
            "af": af_filter,
            "movflags": "+faststart",
        }
    )

    cmd.run(dry_run=dry_run, verbose=True)
    logger.info(f"Normalized: {input_path} -> {output_path}")
    return output_path


def needs_normalization(info: FileInfo,
                        config: Optional[NormalizeConfig] = None) -> bool:
    """Check if a file needs normalization.

    Args:
        info: FileInfo from probe().
        config: Target configuration (uses defaults if None).

    Returns:
        True if the file differs from the target config.
    """
    if config is None:
        config = NormalizeConfig()

    if not info.has_video:
        return True

    v = info.primary_video

    if v.width != config.width or v.height != config.height:
        return True
    if abs(v.fps - config.fps) > 0.1:
        return True
    if v.pix_fmt != config.pix_fmt:
        return True

    # Check audio if present
    if info.has_audio:
        a = info.primary_audio
        if a.sample_rate != config.sample_rate:
            return True
        if (a.channels != 2 and config.channel_layout == "stereo"):
            return True

    return False


def any_needs_normalization(filepaths: list,
                            config: Optional[NormalizeConfig] = None) -> bool:
    """Check if any files in a list need normalization.

    This is a fast check — probes all files and returns True
    if any file differs from the target (or from each other).
    """
    if config is None:
        config = NormalizeConfig()

    for fp in filepaths:
        info = probe(fp)
        if needs_normalization(info, config):
            return True
    return False


def normalize_all(input_paths: list, output_dir: str,
                  config: Optional[NormalizeConfig] = None,
                  dry_run: bool = False) -> list:
    """Normalize all input files, return list of output paths.

    Files that already match the target config are copied (not re-encoded)
    to maintain consistent file naming in the output directory.

    Args:
        input_paths: List of source video paths.
        output_dir: Directory for normalized output files.
        config: Normalization parameters.
        dry_run: If True, print commands without executing.

    Returns:
        List of paths to normalized files (same order as inputs).
    """
    import shutil
    from .utils import temp_filename

    if config is None:
        config = NormalizeConfig()

    output_paths = []
    for i, fp in enumerate(input_paths):
        info = probe(fp)
        out_path = temp_filename(f"norm_{i:03d}", "mp4", output_dir)

        if needs_normalization(info, config):
            logger.info(
                f"Normalizing [{i+1}/{len(input_paths)}]: {fp}"
            )
            normalize(fp, out_path, config, dry_run=dry_run)
        else:
            logger.info(
                f"Skipping normalization [{i+1}/{len(input_paths)}]: "
                f"{fp} (already matches target)"
            )
            if not dry_run:
                shutil.copy2(fp, out_path)

        output_paths.append(out_path)

    return output_paths
