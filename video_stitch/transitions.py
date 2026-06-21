"""Filter-graph builder for video transitions and audio crossfades.

This is the trickiest part of the codebase — constructing the
correct ffmpeg -filter_complex string for xfade transitions.

For N inputs with crossfade duration X:
  offset[i] = sum(d[0..i-1]) - i * X

Total output duration = sum(all durations) - (N-1) * X
  (plus any fade-in/fade-out padding)
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

from .constants import (
    DEFAULT_CROSSFADE_DURATION, DEFAULT_FADE_DURATION,
    SUPPORTED_TRANSITIONS,
)

logger = logging.getLogger("video_stitch")


@dataclass
class TransitionConfig:
    """Configuration for transitions between video segments."""
    crossfade_duration: float = DEFAULT_CROSSFADE_DURATION
    fade_in_duration: float = DEFAULT_FADE_DURATION
    fade_out_duration: float = DEFAULT_FADE_DURATION
    transition_type: str = "crossfade"  # "crossfade" or "fadeblack"

    def validate(self) -> list:
        """Validate transition config. Returns list of error strings."""
        errors = []
        if self.crossfade_duration < 0:
            errors.append("Crossfade duration cannot be negative")
        if self.fade_in_duration < 0:
            errors.append("Fade-in duration cannot be negative")
        if self.fade_out_duration < 0:
            errors.append("Fade-out duration cannot be negative")
        if self.transition_type not in SUPPORTED_TRANSITIONS:
            errors.append(
                f"Unsupported transition type: '{self.transition_type}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_TRANSITIONS))}"
            )
        return errors


def compute_xfade_offsets(durations: List[float],
                          crossfade: float) -> List[float]:
    """Compute xfade offset times for each transition.

    For N inputs with durations d[0]..d[N-1] and crossfade X:
      offset[i] = sum(d[0..i]) - (i+1) * X

    Args:
        durations: Duration of each input segment (after trim).
        crossfade: Crossfade duration in seconds.

    Returns:
        List of N-1 offset values (one per transition).

    Raises:
        ValueError: If crossfade exceeds any segment's duration.
    """
    if crossfade <= 0:
        return [0.0] * (len(durations) - 1)

    offsets = []
    cumulative = 0.0

    for i in range(len(durations) - 1):
        seg_dur = durations[i]
        if crossfade >= seg_dur:
            raise ValueError(
                f"Crossfade duration ({crossfade}s) must be shorter than "
                f"the shortest input segment ({seg_dur}s at segment {i+1}). "
                f"Reduce --crossfade or increase segment duration."
            )

        cumulative += seg_dur
        # Each previous transition has consumed (i) crossfade durations
        # offset = cumulative_duration - crossfade_count * crossfade
        # where crossfade_count = i + 1
        offset = cumulative - (i + 1) * crossfade
        offsets.append(offset)

    return offsets


def build_video_filter_graph(
    input_count: int,
    durations: List[float],
    config: TransitionConfig,
    label_prefix: str = "v",
    stream_suffix: str = "v",
) -> str:
    """Build the video filter_complex graph for stitching.

    For 3 inputs with crossfade 0.5s, fade-in 1s, fade-out 1.5s,
    with durations [3, 4, 5]:

    Chain: [0:v][1:v]xfade=...;[x1][2:v]xfade=...;[x2]fade=...

    Args:
        input_count: Number of input files.
        durations: Duration of each input in seconds.
        config: Transition configuration.
        label_prefix: Prefix for intermediate labels (e.g., "v" -> "x1", "x2").
        stream_suffix: Stream specifier suffix (e.g., "v" for video).

    Returns:
        A complete -filter_complex string.

    Raises:
        ValueError: If configuration is invalid.
    """
    errors = config.validate()
    if errors:
        raise ValueError("Invalid transition config: " + "; ".join(errors))

    if input_count < 1:
        raise ValueError("Need at least 1 input for filter graph")

    if len(durations) != input_count:
        raise ValueError(
            f"Duration count ({len(durations)}) must match "
            f"input count ({input_count})"
        )

    parts = []

    # If only one input, just apply fades directly
    if input_count == 1:
        fade_filters = _build_single_fade_filters(config, durations[0])
        if fade_filters:
            parts.append(f"[0:{stream_suffix}]{fade_filters}[{label_prefix}]")
        else:
            parts.append(f"[0:{stream_suffix}]null[{label_prefix}]")
        return ";".join(parts)

    # Multiple inputs: chain xfade transitions
    prev_label = f"0:{stream_suffix}"
    next_label_idx = 1

    if config.crossfade_duration > 0:
        offsets = compute_xfade_offsets(durations, config.crossfade_duration)

        for i in range(len(offsets)):
            inter_label = f"x{next_label_idx}"
            offset = offsets[i]
            duration = config.crossfade_duration
            transition = _xfade_transition_name(config.transition_type)

            parts.append(
                f"[{prev_label}][{next_label_idx}:{stream_suffix}]"
                f"xfade=transition={transition}:"
                f"duration={duration:.3f}:"
                f"offset={offset:.3f}"
                f"[{inter_label}]"
            )
            prev_label = inter_label
            next_label_idx += 1
    else:
        # No crossfade: use simple concat filter
        stream_labels = "".join(
            f"[{i}:{stream_suffix}]" for i in range(input_count)
        )
        parts.append(f"{stream_labels}concat=n={input_count}:v=1:a=0[x1]")
        prev_label = "x1"

    # Apply fade-in/out to the final chain output
    total_duration = sum(durations)
    if config.crossfade_duration > 0:
        total_duration -= (input_count - 1) * config.crossfade_duration

    fade_filters = _build_fade_filters(config, total_duration)
    if fade_filters:
        parts.append(f"[{prev_label}]{fade_filters}[{label_prefix}]")
    else:
        parts.append(f"[{prev_label}]null[{label_prefix}]")

    return ";".join(parts)


def build_audio_filter_graph(
    input_count: int,
    durations: List[float],
    config: TransitionConfig,
    label_prefix: str = "a",
    stream_suffix: str = "a",
) -> str:
    """Build the audio filter_complex graph for crossfading.

    Uses acrossfade filter for transitions between audio streams.

    Args:
        input_count: Number of input files.
        durations: Duration of each input in seconds.
        config: Transition configuration.
        label_prefix: Prefix for output label.
        stream_suffix: Stream specifier suffix (e.g., "a" for audio).

    Returns:
        A complete -filter_complex string for audio.

    Raises:
        ValueError: If configuration is invalid.
    """
    if input_count < 1:
        raise ValueError("Need at least 1 input for audio filter graph")

    parts = []

    if input_count == 1:
        fade_filters = _build_single_audio_fade_filters(config, durations[0])
        if fade_filters:
            parts.append(f"[0:{stream_suffix}]{fade_filters}[{label_prefix}]")
        else:
            parts.append(f"[0:{stream_suffix}]anull[{label_prefix}]")
        return ";".join(parts)

    prev_label = f"0:{stream_suffix}"
    next_label_idx = 1

    if config.crossfade_duration > 0:
        for i in range(input_count - 1):
            inter_label = f"xa{next_label_idx}"
            duration = config.crossfade_duration

            # acrossfade uses a different offset: the overlap between streams
            parts.append(
                f"[{prev_label}][{next_label_idx}:{stream_suffix}]"
                f"acrossfade=d={duration:.3f}:c1=tri:c2=tri"
                f"[{inter_label}]"
            )
            prev_label = inter_label
            next_label_idx += 1
    else:
        stream_labels = "".join(
            f"[{i}:{stream_suffix}]" for i in range(input_count)
        )
        parts.append(f"{stream_labels}concat=n={input_count}:v=0:a=1[xa1]")
        prev_label = "xa1"

    # Apply fade-in/out to the final audio
    total_duration = sum(durations)
    if config.crossfade_duration > 0:
        total_duration -= (input_count - 1) * config.crossfade_duration

    fade_filters = _build_audio_fade_filters(config, total_duration)
    if fade_filters:
        parts.append(f"[{prev_label}]{fade_filters}[{label_prefix}]")
    else:
        parts.append(f"[{prev_label}]anull[{label_prefix}]")

    return ";".join(parts)


def total_output_duration(durations: List[float],
                          config: TransitionConfig) -> float:
    """Compute the total duration of the stitched output.

    Args:
        durations: Duration of each input segment.
        config: Transition configuration.

    Returns:
        Total output duration in seconds.
    """
    total = sum(durations)
    if config.crossfade_duration > 0 and len(durations) > 1:
        total -= (len(durations) - 1) * config.crossfade_duration
    return max(0, total)


# --- Internal helpers ---

def _xfade_transition_name(transition_type: str) -> str:
    """Map user-facing transition names to ffmpeg xfade transition values."""
    mapping = {
        "crossfade": "fade",
        "fadeblack": "fadeblack",
    }
    return mapping.get(transition_type, "fade")


def _build_fade_filters(config: TransitionConfig,
                        total_duration: float) -> str:
    """Build fade-in/out filter string for video."""
    filters = []
    if config.fade_in_duration > 0:
        filters.append(f"fade=t=in:d={config.fade_in_duration:.3f}")
    if config.fade_out_duration > 0:
        start_time = total_duration - config.fade_out_duration
        filters.append(
            f"fade=t=out:d={config.fade_out_duration:.3f}:"
            f"st={start_time:.3f}"
        )
    return ",".join(filters) if filters else ""


def _build_single_fade_filters(config: TransitionConfig,
                               total_duration: float) -> str:
    """Build fade filters for a single video (no xfade needed)."""
    return _build_fade_filters(config, total_duration)


def _build_audio_fade_filters(config: TransitionConfig,
                              total_duration: float) -> str:
    """Build fade-in/out filter string for audio."""
    filters = []
    if config.fade_in_duration > 0:
        filters.append(f"afade=t=in:d={config.fade_in_duration:.3f}")
    if config.fade_out_duration > 0:
        start_time = total_duration - config.fade_out_duration
        filters.append(
            f"afade=t=out:d={config.fade_out_duration:.3f}:"
            f"st={start_time:.3f}"
        )
    return ",".join(filters) if filters else ""


def _build_single_audio_fade_filters(config: TransitionConfig,
                                     total_duration: float) -> str:
    """Build audio fade filters for a single audio stream."""
    return _build_audio_fade_filters(config, total_duration)
