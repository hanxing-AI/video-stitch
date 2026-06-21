"""Command-line interface for video-stitch."""

import sys
import argparse
import logging
from typing import List, Optional

from . import __version__

logger = logging.getLogger("video_stitch")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the video-stitch CLI."""
    parser = argparse.ArgumentParser(
        prog="video-stitch",
        description="Stitch multiple video clips into one, with transitions, "
                    "text overlays, auto-normalization, trim, and fade effects.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple concatenation
  video-stitch -o final.mp4 clip1.mp4 clip2.mp4 clip3.mp4

  # With crossfade and fades
  video-stitch -o final.mp4 --crossfade 0.5 --fade-in 1 --fade-out 1.5 *.mp4

  # Trim and concatenate
  video-stitch -o final.mp4 --trim 5-30 --trim 0-15 clip1.mp4 clip2.mp4

  # Add title and watermark
  video-stitch -o final.mp4 --title "My Lecture" --watermark "(c) 2026" *.mp4

  # Auto-normalize mixed resolutions
  video-stitch -o final.mp4 --target-resolution 1920x1080 --target-fps 30 *.mp4

  # Use a recipe file for repeatable projects
  video-stitch --recipe my-project.json

  # Preview without executing
  video-stitch --dry-run -o final.mp4 --crossfade 0.5 *.mp4

  # Probe video info
  video-stitch --probe clip1.mp4
        """,
    )

    # Positional: input files (unless --recipe or --probe is used)
    parser.add_argument(
        "inputs", nargs="*",
        help="Input video files to stitch together",
    )

    parser.add_argument(
        "-o", "--output",
        help="Output file path (required unless --recipe or --probe)",
    )

    # Recipe mode
    parser.add_argument(
        "--recipe",
        help="Path to a recipe JSON file (overrides most other flags)",
    )

    # Probe mode
    parser.add_argument(
        "--probe", action="store_true",
        help="Print video file info and exit",
    )

    # Trim
    parser.add_argument(
        "--trim", action="append",
        help="Trim specification: 'start-end', 'start-', '-end', or 'duration'. "
             "Repeat for per-file trim. Example: --trim 5-30 --trim 0-15",
    )

    # Normalize
    parser.add_argument(
        "--no-normalize", action="store_true",
        help="Skip auto-normalization (use if all files have same resolution)",
    )
    parser.add_argument(
        "--target-resolution", default="1920x1080",
        help="Target resolution for normalization (WxH, default: 1920x1080)",
    )
    parser.add_argument(
        "--target-fps", type=float, default=30.0,
        help="Target framerate for normalization (default: 30)",
    )

    # Transitions
    parser.add_argument(
        "--crossfade", type=float, default=0.0,
        help="Crossfade duration in seconds (default: 0 = no crossfade)",
    )
    parser.add_argument(
        "--transition-type", default="crossfade",
        choices=["crossfade", "fadeblack"],
        help="Type of transition (default: crossfade)",
    )

    # Edge effects
    parser.add_argument(
        "--fade-in", type=float, default=0.0,
        help="Fade-in duration in seconds (default: 0)",
    )
    parser.add_argument(
        "--fade-out", type=float, default=0.0,
        help="Fade-out duration in seconds (default: 0)",
    )

    # Text overlays
    parser.add_argument(
        "--title",
        help="Title card text (shown centered at start of video)",
    )
    parser.add_argument(
        "--title-duration", type=float, default=3.0,
        help="How long to show the title (seconds, default: 3)",
    )
    parser.add_argument(
        "--watermark",
        help="Watermark text (shown throughout the video)",
    )
    parser.add_argument(
        "--watermark-position", default="bottom-right",
        choices=["bottom-right", "bottom-left", "top-right", "top-left"],
        help="Watermark position (default: bottom-right)",
    )
    parser.add_argument(
        "--font-file",
        help="Path to a .ttf/.otf font file for text overlays",
    )
    parser.add_argument(
        "--font-size", type=int, default=48,
        help="Font size for text overlays (default: 48)",
    )
    parser.add_argument(
        "--text-color", default="white",
        help="Text color for overlays (default: white)",
    )

    # Output options
    parser.add_argument(
        "--output-format", default="mp4",
        choices=["mp4", "webm", "mkv", "mov"],
        help="Output container format (default: mp4)",
    )
    parser.add_argument(
        "--preset", default="medium",
        choices=["fast", "medium", "slow", "veryslow", "ultrafast", "slower"],
        help="H.264 encoding preset (default: medium)",
    )
    parser.add_argument(
        "--crf", type=int, default=23,
        help="H.264 quality (0-51, lower = better, default: 23)",
    )

    # Operational
    parser.add_argument(
        "--keep-temp", action="store_true",
        help="Keep temporary files for debugging",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print ffmpeg commands without executing",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"video-stitch {__version__}",
    )

    return parser


def _setup_logging(verbose: bool):
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s" if not verbose
        else "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )


def probe_main():
    """Entry point for the 'video-probe' console script."""
    parser = argparse.ArgumentParser(
        prog="video-probe",
        description="Print detailed info about video files.",
    )
    parser.add_argument("files", nargs="+", help="Video files to probe")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON")
    args = parser.parse_args()

    from .probe import probe, probe_json, probe_summary

    for fp in args.files:
        if args.json:
            print(probe_json(fp))
        else:
            print(probe_summary(fp))


def main():
    """Main entry point for the 'video-stitch' console script."""
    parser = build_parser()
    args = parser.parse_args()

    _setup_logging(args.verbose)

    # --probe mode: print info and exit
    if args.probe:
        if not args.inputs:
            parser.error("--probe requires at least one input file")
        from .probe import probe_summary
        for fp in args.inputs:
            print(probe_summary(fp))
        return

    # --recipe mode: load from JSON
    if args.recipe:
        from .recipe import load_recipe, recipe_to_stitch_job
        from .stitcher import StitchJob, run

        recipe = load_recipe(args.recipe)
        kwargs = recipe_to_stitch_job(recipe)
        kwargs["dry_run"] = args.dry_run
        kwargs["verbose"] = args.verbose
        kwargs["keep_temp"] = args.keep_temp

        job = StitchJob(**kwargs)
        run(job)
        return

    # Direct CLI mode
    if not args.inputs:
        parser.error("At least one input file is required (or use --recipe)")
    if not args.output:
        parser.error("--output is required (or use --recipe)")

    # Parse trims
    from .trimmer import parse_trim
    trims = []
    if args.trim:
        for i, t_spec in enumerate(args.trim):
            trims.append(parse_trim(t_spec))

    # Build StitchJob
    from .stitcher import StitchJob, run

    job = StitchJob(
        inputs=args.inputs,
        output=args.output,
        trims=trims if trims else [],
        normalize=not args.no_normalize,
        target_resolution=args.target_resolution,
        target_fps=args.target_fps,
        crossfade=args.crossfade,
        fade_in=args.fade_in,
        fade_out=args.fade_out,
        transition_type=args.transition_type,
        title_text=args.title,
        title_duration=args.title_duration,
        watermark_text=args.watermark,
        watermark_position=args.watermark_position,
        font_file=args.font_file,
        font_size=args.font_size,
        text_color=args.text_color,
        output_format=args.output_format,
        preset=args.preset,
        crf=args.crf,
        keep_temp=args.keep_temp,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    run(job)


if __name__ == "__main__":
    main()
