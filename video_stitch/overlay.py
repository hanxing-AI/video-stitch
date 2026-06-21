"""Text overlay builder using ffmpeg's drawtext filter.

Supports title cards (timed text display) and watermarks (persistent text).
"""

import logging
from dataclasses import dataclass
from typing import Optional

from .constants import (
    DEFAULT_FONT_SIZE, DEFAULT_FONT_COLOR, DEFAULT_TITLE_DURATION,
    DEFAULT_BORDER_COLOR, DEFAULT_BORDER_WIDTH,
    WATERMARK_POSITIONS,
)

logger = logging.getLogger("video_stitch")


@dataclass
class TextOverlay:
    """Configuration for a text overlay on video.

    For drawtext filter reference:
    https://ffmpeg.org/ffmpeg-filters.html#drawtext
    """
    text: str
    x_expr: str = "(main_w-text_w)/2"   # ffmpeg drawtext x expression
    y_expr: str = "(main_h-text_h)/2"   # ffmpeg drawtext y expression
    font_size: int = DEFAULT_FONT_SIZE
    font_color: str = DEFAULT_FONT_COLOR
    font_file: Optional[str] = None
    enable_expr: str = "between(t,0,3)"  # show between these times
    border_width: int = DEFAULT_BORDER_WIDTH
    border_color: str = DEFAULT_BORDER_COLOR
    alpha: float = 1.0

    def validate(self) -> list:
        """Validate overlay config. Returns list of error strings."""
        errors = []
        if not self.text:
            errors.append("Text cannot be empty")
        if self.font_size <= 0:
            errors.append(f"Font size must be positive: {self.font_size}")
        if not (0.0 <= self.alpha <= 1.0):
            errors.append(f"Alpha must be between 0 and 1: {self.alpha}")
        return errors


def title_card(
    text: str,
    duration: float = DEFAULT_TITLE_DURATION,
    font_size: int = 72,
    font_color: str = "white",
    font_file: Optional[str] = None,
) -> TextOverlay:
    """Create a centered title card overlay.

    Displays text centered on screen from t=0 to t=duration.

    Args:
        text: Title text to display.
        duration: How long to show the title (seconds).
        font_size: Font size in pixels.
        font_color: Color name or hex code.
        font_file: Optional path to .ttf/.otf font file.

    Returns:
        TextOverlay configured as a title card.
    """
    return TextOverlay(
        text=text,
        x_expr="(main_w-text_w)/2",
        y_expr="(main_h-text_h)/2",
        font_size=font_size,
        font_color=font_color,
        font_file=font_file,
        enable_expr=f"between(t,0,{duration:.3f})",
        border_width=2,
        border_color="black@0.5",
    )


def watermark(
    text: str,
    position: str = "bottom-right",
    font_size: int = 24,
    font_color: str = "white@0.7",
    font_file: Optional[str] = None,
) -> TextOverlay:
    """Create a persistent watermark overlay.

    Args:
        text: Watermark text.
        position: One of "bottom-right", "bottom-left", "top-right",
                  "top-left", "center".
        font_size: Font size in pixels.
        font_color: Color (supports alpha via @ notation, e.g., "white@0.7").
        font_file: Optional path to .ttf/.otf font file.

    Returns:
        TextOverlay configured as a watermark.

    Raises:
        ValueError: If position is not recognized.
    """
    if position not in WATERMARK_POSITIONS:
        raise ValueError(
            f"Unknown position: '{position}'. "
            f"Choose from: {', '.join(WATERMARK_POSITIONS.keys())}"
        )

    x_expr, y_expr = WATERMARK_POSITIONS[position].split(":", 1)

    return TextOverlay(
        text=text,
        x_expr=x_expr,
        y_expr=y_expr,
        font_size=font_size,
        font_color=font_color,
        font_file=font_file,
        enable_expr="between(t,0,999999)",  # Always on
        border_width=1,
        border_color="black@0.3",
    )


def build_drawtext_filter(overlay: TextOverlay) -> str:
    """Build a single drawtext filter string.

    Handles escaping of special characters in text for ffmpeg.

    Args:
        overlay: The text overlay configuration.

    Returns:
        A complete drawtext filter string ready for -vf or -filter_complex.
    """
    text_escaped = _escape_drawtext(overlay.text)
    font_color_escaped = _escape_drawtext(overlay.font_color)

    parts = [
        f"drawtext=text='{text_escaped}'",
        f"fontsize={overlay.font_size}",
        f"fontcolor={font_color_escaped}",
        f"x={overlay.x_expr}",
        f"y={overlay.y_expr}",
        f"enable='{overlay.enable_expr}'",
        f"bordercolor={_escape_drawtext(overlay.border_color)}",
        f"borderw={overlay.border_width}",
    ]

    if overlay.font_file:
        # Normalize path for ffmpeg
        font_path = overlay.font_file.replace("\\", "/")
        parts.insert(1, f"fontfile='{_escape_drawtext(font_path)}'")

    if overlay.alpha < 1.0:
        parts.append(f"alpha={overlay.alpha:.2f}")

    return ":".join(parts)


def build_overlay_chain(overlays: list, base_label: str = "base",
                        output_label: str = "v") -> str:
    """Build a filter_complex chain applying multiple text overlays.

    Each overlay is applied as a separate drawtext step so they can have
    independent timings.

    Args:
        overlays: List of TextOverlay objects to apply.
        base_label: Label of the input video stream.
        output_label: Label for the final output stream.

    Returns:
        A filter_complex string segment for the overlay chain.
        Empty string if overlays is empty.
    """
    if not overlays:
        return ""

    parts = []
    prev_label = base_label
    for i, ov in enumerate(overlays):
        inter_label = f"ov{i}" if i < len(overlays) - 1 else output_label
        dt = build_drawtext_filter(ov)
        parts.append(f"[{prev_label}]{dt}[{inter_label}]")
        prev_label = inter_label

    return ";".join(parts)


def find_system_font() -> Optional[str]:
    """Try to find a usable TrueType font on the system.

    Checks common font directories on Windows, macOS, and Linux.
    Returns the path to the first found font, or None.
    """
    import os
    import platform

    candidates = []

    if platform.system() == "Windows":
        font_dir = os.environ.get("WINDIR", "C:\\Windows") + "\\Fonts"
        candidates = [
            os.path.join(font_dir, "arial.ttf"),
            os.path.join(font_dir, "segoeui.ttf"),
            os.path.join(font_dir, "calibri.ttf"),
        ]
    elif platform.system() == "Darwin":
        candidates = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFNSText.ttf",
            "/Library/Fonts/Arial.ttf",
        ]
    else:  # Linux
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]

    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _escape_drawtext(text: str) -> str:
    r"""Escape special characters for ffmpeg's drawtext filter.

    Handles backslash, single quote, colon, and percent.
    """
    # Order matters: escape backslash first
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\\'")
    text = text.replace(":", "\\:")
    text = text.replace("%", "\\%")
    return text
