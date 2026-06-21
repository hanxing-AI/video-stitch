"""Tests for cli.py."""

import sys
import pytest
from video_stitch.cli import build_parser


class TestParser:
    def test_basic_parse(self):
        parser = build_parser()
        args = parser.parse_args(["-o", "out.mp4", "a.mp4", "b.mp4"])
        assert args.output == "out.mp4"
        assert args.inputs == ["a.mp4", "b.mp4"]

    def test_no_inputs_defaults(self):
        parser = build_parser()
        # With nargs="*", empty inputs are allowed by argparse
        # Validation happens in main(), not in the parser
        args = parser.parse_args([])
        assert args.inputs == []
        assert args.output is None

    def test_with_crossfade(self):
        parser = build_parser()
        args = parser.parse_args([
            "-o", "out.mp4", "--crossfade", "0.5", "a.mp4"
        ])
        assert args.crossfade == 0.5

    def test_with_fades(self):
        parser = build_parser()
        args = parser.parse_args([
            "-o", "out.mp4", "--fade-in", "1.0", "--fade-out", "2.0", "a.mp4"
        ])
        assert args.fade_in == 1.0
        assert args.fade_out == 2.0

    def test_with_title(self):
        parser = build_parser()
        args = parser.parse_args([
            "-o", "out.mp4", "--title", "My Title", "a.mp4"
        ])
        assert args.title == "My Title"

    def test_with_watermark(self):
        parser = build_parser()
        args = parser.parse_args([
            "-o", "out.mp4", "--watermark", "(c)", "--watermark-position", "top-right", "a.mp4"
        ])
        assert args.watermark == "(c)"
        assert args.watermark_position == "top-right"

    def test_with_trim(self):
        parser = build_parser()
        args = parser.parse_args([
            "-o", "out.mp4", "--trim", "5-30", "--trim", "0-15", "a.mp4", "b.mp4"
        ])
        assert args.trim == ["5-30", "0-15"]

    def test_no_normalize(self):
        parser = build_parser()
        args = parser.parse_args([
            "-o", "out.mp4", "--no-normalize", "a.mp4"
        ])
        assert args.no_normalize

    def test_output_format(self):
        parser = build_parser()
        args = parser.parse_args([
            "-o", "out.webm", "--output-format", "webm", "a.mp4"
        ])
        assert args.output_format == "webm"

    def test_preset_and_crf(self):
        parser = build_parser()
        args = parser.parse_args([
            "-o", "out.mp4", "--preset", "fast", "--crf", "18", "a.mp4"
        ])
        assert args.preset == "fast"
        assert args.crf == 18

    def test_dry_run(self):
        parser = build_parser()
        args = parser.parse_args([
            "-o", "out.mp4", "--dry-run", "a.mp4"
        ])
        assert args.dry_run

    def test_verbose(self):
        parser = build_parser()
        args = parser.parse_args([
            "-o", "out.mp4", "--verbose", "a.mp4"
        ])
        assert args.verbose

    def test_probe_mode(self):
        parser = build_parser()
        args = parser.parse_args(["--probe", "a.mp4"])
        assert args.probe
        assert args.inputs == ["a.mp4"]

    def test_recipe_mode(self):
        parser = build_parser()
        args = parser.parse_args(["--recipe", "test.json"])
        assert args.recipe == "test.json"

    def test_version(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])
