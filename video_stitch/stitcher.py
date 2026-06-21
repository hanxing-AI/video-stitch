"""Main orchestrator — coordinates the full video stitching pipeline.

Phase 1: Probe all inputs
Phase 2: Apply trim to each input -> temp files
Phase 3: Normalize trimmed files -> temp files (if enabled)
Phase 4: Build filter graph (xfade + fades + text overlays)
Phase 5: Execute stitch ffmpeg command
Phase 6: Clean up temp files (unless --keep-temp)
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from .probe import probe, FileInfo, find_common_params
from .trimmer import TrimSpec, apply_trim
from .normalizer import (
    NormalizeConfig, normalize, needs_normalization,
    any_needs_normalization, normalize_all,
)
from .transitions import (
    TransitionConfig,
    build_video_filter_graph,
    build_audio_filter_graph,
    total_output_duration,
)
from .overlay import TextOverlay, build_overlay_chain
from .pipeline import FFmpegCommand
from .utils import temp_dir, temp_filename, format_duration
from .constants import (
    DEFAULT_RESOLUTION, DEFAULT_FPS, DEFAULT_VIDEO_CODEC,
    DEFAULT_CRF, DEFAULT_PRESET, DEFAULT_PIX_FMT,
    DEFAULT_AUDIO_CODEC, DEFAULT_AUDIO_BITRATE,
    DEFAULT_SAMPLE_RATE, DEFAULT_CHANNEL_LAYOUT,
    DEFAULT_FONT_SIZE, DEFAULT_FONT_COLOR,
    SUPPORTED_CONTAINERS,
)

logger = logging.getLogger("video_stitch")


@dataclass
class StitchJob:
    """Complete specification for a video stitching operation.

    All parameters have sensible defaults. The only required fields
    are `inputs` and `output`.
    """
    inputs: List[str] = field(default_factory=list)
    output: str = "output.mp4"

    # Trim
    trims: List[Optional[TrimSpec]] = field(default_factory=list)

    # Normalize
    normalize: bool = True
    normalize_config: Optional[NormalizeConfig] = None
    target_resolution: str = "1920x1080"
    target_fps: float = 30.0

    # Transitions
    crossfade: float = 0.0
    fade_in: float = 0.0
    fade_out: float = 0.0
    transition_type: str = "crossfade"

    # Text overlays
    title_text: Optional[str] = None
    title_duration: float = 3.0
    watermark_text: Optional[str] = None
    watermark_position: str = "bottom-right"
    font_file: Optional[str] = None
    font_size: int = DEFAULT_FONT_SIZE
    text_color: str = DEFAULT_FONT_COLOR

    # Output
    output_format: str = "mp4"
    preset: str = DEFAULT_PRESET
    crf: int = DEFAULT_CRF

    # Operational
    keep_temp: bool = False
    dry_run: bool = False
    verbose: bool = False

    def validate(self) -> list:
        """Validate the stitch job. Returns list of error strings."""
        errors = []

        if not self.inputs:
            errors.append("At least one input file is required")
        if len(self.inputs) < 1:
            errors.append("At least one input file is required")

        if self.output_format not in SUPPORTED_CONTAINERS:
            errors.append(
                f"Unsupported output format: '{self.output_format}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_CONTAINERS))}"
            )

        if self.crossfade < 0:
            errors.append("Crossfade duration cannot be negative")
        if self.fade_in < 0:
            errors.append("Fade-in duration cannot be negative")
        if self.fade_out < 0:
            errors.append("Fade-out duration cannot be negative")
        if self.title_duration < 0:
            errors.append("Title duration cannot be negative")
        if self.font_size <= 0:
            errors.append("Font size must be positive")
        if self.crf < 0 or self.crf > 51:
            errors.append(f"CRF must be between 0 and 51: {self.crf}")

        # Parse resolution if provided
        try:
            w, h = self.target_resolution.split("x")
            if int(w) <= 0 or int(h) <= 0:
                errors.append(f"Invalid resolution: {self.target_resolution}")
        except (ValueError, AttributeError):
            errors.append(
                f"Resolution must be WxH format: '{self.target_resolution}'"
            )

        if self.target_fps <= 0:
            errors.append(f"Target FPS must be positive: {self.target_fps}")

        return errors


def run(job: StitchJob) -> str:
    """Execute a full video stitching pipeline.

    This is the main entry point. It coordinates all phases of the
    stitching process and returns the path to the output file.

    Args:
        job: A configured StitchJob with all parameters.

    Returns:
        Path to the output video file.

    Raises:
        ValueError: If job validation fails.
        FileNotFoundError: If any input file doesn't exist.
        RuntimeError: If ffmpeg fails at any stage.
    """
    # Validate
    errors = job.validate()
    if errors:
        raise ValueError("Invalid stitch job:\n  " + "\n  ".join(errors))

    # Check inputs exist
    for fp in job.inputs:
        if not os.path.exists(fp):
            raise FileNotFoundError(f"Input file not found: {fp}")

    if job.verbose:
        logger.info(f"Starting stitch job: {len(job.inputs)} inputs -> {job.output}")
        for i, fp in enumerate(job.inputs):
            logger.info(f"  [{i+1}] {fp}")

    # Build normalize config
    norm_config = job.normalize_config
    if norm_config is None and job.normalize:
        try:
            w, h = job.target_resolution.split("x")
            norm_config = NormalizeConfig(
                width=int(w), height=int(h), fps=job.target_fps,
            )
        except (ValueError, AttributeError):
            norm_config = NormalizeConfig()

    # Build transition config
    trans_config = TransitionConfig(
        crossfade_duration=job.crossfade,
        fade_in_duration=job.fade_in,
        fade_out_duration=job.fade_out,
        transition_type=job.transition_type,
    )

    # Build overlay list
    overlays = []

    # Auto-detect font if overlays are needed and no font specified
    font = job.font_file
    if (job.title_text or job.watermark_text) and not font:
        from .overlay import find_system_font
        font = find_system_font()
        if not font:
            logger.warning(
                "No system font found and --font-file not specified. "
                "Text overlays may fail. Install a font or use --font-file."
            )

    if job.title_text:
        from .overlay import title_card
        overlays.append(title_card(
            job.title_text,
            duration=job.title_duration,
            font_size=job.font_size,
            font_color=job.text_color,
            font_file=font,
        ))
    if job.watermark_text:
        from .overlay import watermark
        overlays.append(watermark(
            job.watermark_text,
            position=job.watermark_position,
            font_size=job.font_size,
            font_color=f"{job.text_color}@0.7",
            font_file=font,
        ))

    with temp_dir(prefix="video-stitch-", keep=job.keep_temp) as tmp:
        # Phase 1: Probe all inputs
        if job.verbose:
            logger.info("Phase 1: Probing inputs...")
        file_infos = []
        for fp in job.inputs:
            info = probe(fp)
            file_infos.append(info)
            if job.verbose:
                dur_str = format_duration(info.duration)
                res = f"{info.primary_video.width}x{info.primary_video.height}" if info.primary_video else "no video"
                logger.info(f"  {os.path.basename(fp)}: {res}, {dur_str}")

        # Phase 2: Trim inputs
        if job.trims and any(t is not None for t in job.trims):
            if job.verbose:
                logger.info("Phase 2: Trimming inputs...")
            trimmed_paths = []
            for i, (fp, info) in enumerate(zip(job.inputs, file_infos)):
                trim = None
                if i < len(job.trims):
                    trim = job.trims[i]
                if trim is None:
                    # No trim for this input: copy directly
                    trimmed_paths.append(fp)
                    continue

                out_path = temp_filename(f"trim_{i:03d}", "mp4", tmp)
                apply_trim(fp, out_path, trim,
                          total_duration=info.duration,
                          dry_run=job.dry_run)
                trimmed_paths.append(out_path)

                # Re-probe the trimmed file for accurate duration
                file_infos[i] = probe(out_path)
        else:
            trimmed_paths = list(job.inputs)

        # Phase 3: Normalize
        working_paths = list(trimmed_paths)
        if job.normalize:
            should_norm = any_needs_normalization(working_paths, norm_config)
            if should_norm:
                if job.verbose:
                    logger.info("Phase 3: Normalizing inputs...")
                working_paths = normalize_all(
                    working_paths, tmp, norm_config, dry_run=job.dry_run
                )
                # Re-probe normalized files
                for i, fp in enumerate(working_paths):
                    if fp != trimmed_paths[i]:  # Only if actually normalized
                        file_infos[i] = probe(fp)
            else:
                if job.verbose:
                    logger.info("Phase 3: Skipping (all files match target)")

        # Extract durations for filter graph
        durations = [info.duration for info in file_infos]
        if job.verbose:
            logger.info(f"Segment durations: {[f'{d:.1f}s' for d in durations]}")

        # Phase 4: Build filter graph
        if job.verbose:
            logger.info("Phase 4: Building filter graph...")

        video_graph = build_video_filter_graph(
            len(working_paths), durations, trans_config,
            label_prefix="v", stream_suffix="v",
        )

        # Check if any inputs have audio
        has_audio = all(info.has_audio for info in file_infos)
        audio_graph = ""
        if has_audio:
            audio_graph = build_audio_filter_graph(
                len(working_paths), durations, trans_config,
                label_prefix="a", stream_suffix="a",
            )

        # Add overlay chain
        full_filter = video_graph
        if overlays:
            overlay_chain = build_overlay_chain(overlays, "v", "vfinal")
            full_filter += ";" + overlay_chain
            video_output_label = "vfinal"
        else:
            video_output_label = "v"

        if has_audio:
            full_filter += ";" + audio_graph

        if job.dry_run:
            logger.info(f"Filter graph:\n{full_filter}")

        # Phase 5: Execute stitch
        if job.verbose:
            logger.info("Phase 5: Stitching...")
            out_dur = total_output_duration(durations, trans_config)
            logger.info(f"  Estimated output duration: {format_duration(out_dur)}")

        cmd = FFmpegCommand()
        cmd.set_boolean("y")

        for fp in working_paths:
            cmd.add_input(fp)

        cmd.set_filter_complex(full_filter)
        cmd.add_map(f"[{video_output_label}]")

        if has_audio:
            cmd.add_map("[a]")

        # Output options
        output_opts = {
            "c:v": DEFAULT_VIDEO_CODEC,
            "preset": job.preset,
            "crf": str(job.crf),
            "pix_fmt": DEFAULT_PIX_FMT,
            "movflags": "+faststart",
        }

        if has_audio:
            output_opts.update({
                "c:a": DEFAULT_AUDIO_CODEC,
                "b:a": DEFAULT_AUDIO_BITRATE,
            })

        cmd.add_output(job.output, **output_opts)
        cmd.run(dry_run=job.dry_run, verbose=job.verbose)

        if job.dry_run:
            logger.info(f"[DRY RUN] Would have written: {job.output}")
        else:
            logger.info(f"Phase 6: Done! Output: {job.output}")

    return job.output
