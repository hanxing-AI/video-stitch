"""Tests for trimmer.py."""

import os
import pytest
from video_stitch.trimmer import TrimSpec, parse_trim, apply_trim
from video_stitch.probe import probe


class TestTrimSpec:
    def test_default(self):
        t = TrimSpec()
        assert t.start == 0.0
        assert t.end is None
        assert t.duration is None

    def test_start_end(self):
        t = TrimSpec(start=5.0, end=30.0)
        assert t.effective_duration == 25.0

    def test_duration(self):
        t = TrimSpec(start=5.0, duration=15.0)
        assert t.effective_duration == 15.0

    def test_validate_start_negative(self):
        t = TrimSpec(start=-1.0)
        errors = t.validate()
        assert len(errors) > 0

    def test_validate_end_before_start(self):
        t = TrimSpec(start=10, end=5)
        errors = t.validate()
        assert len(errors) > 0

    def test_validate_duration_negative(self):
        t = TrimSpec(start=0, duration=-5)
        errors = t.validate()
        assert len(errors) > 0


class TestParseTrim:
    def test_start_end(self):
        t = parse_trim("5.0-30.0")
        assert t.start == 5.0
        assert t.end == 30.0

    def test_start_only(self):
        t = parse_trim("10-")
        assert t.start == 10.0
        assert t.end is None

    def test_end_only(self):
        t = parse_trim("-20")
        assert t.start == 0.0
        assert t.end == 20.0

    def test_plain_number(self):
        t = parse_trim("15")
        assert t.start == 0.0
        assert t.duration == 15.0

    def test_mm_ss_format(self):
        t = parse_trim("1:30-2:00")
        assert t.start == 90.0
        assert t.end == 120.0

    def test_invalid(self):
        with pytest.raises(ValueError):
            parse_trim("-")
        with pytest.raises(ValueError):
            parse_trim("abc")


class TestApplyTrim:
    def test_trim_middle_section(self, sample_video_1080p, tmp_path):
        """Trim a 3-second video to the middle 1.5 seconds."""
        out = str(tmp_path / "trimmed.mp4")
        trim = TrimSpec(start=0.5, end=2.0)
        result = apply_trim(sample_video_1080p, out, trim, total_duration=3.0)
        assert result == out
        assert os.path.exists(out)

        info = probe(out)
        # Duration should be approximately 1.5s
        assert 1.0 < info.duration < 2.0

    def test_trim_with_duration(self, sample_video_1080p, tmp_path):
        """Trim first 1 second of video."""
        out = str(tmp_path / "trimmed_dur.mp4")
        trim = TrimSpec(start=0.0, duration=1.0)
        result = apply_trim(sample_video_1080p, out, trim, total_duration=3.0)
        assert os.path.exists(out)

        info = probe(out)
        assert info.duration < 1.5

    def test_trim_validation(self, sample_video_1080p, tmp_path):
        """Invalid trim should raise ValueError before running ffmpeg."""
        out = str(tmp_path / "trimmed.mp4")
        trim = TrimSpec(start=5.0, end=10.0)  # beyond 3s video
        with pytest.raises(ValueError, match="beyond video duration"):
            apply_trim(sample_video_1080p, out, trim, total_duration=3.0)

    def test_dry_run(self, sample_video_1080p, tmp_path):
        out = str(tmp_path / "trimmed_dry.mp4")
        trim = TrimSpec(start=0, end=1)
        apply_trim(sample_video_1080p, out, trim, dry_run=True)
        assert not os.path.exists(out)
