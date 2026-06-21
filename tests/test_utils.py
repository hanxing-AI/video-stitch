"""Tests for utils.py."""

import os
import pytest
from video_stitch.utils import (
    parse_time, format_duration, temp_dir, temp_filename,
    ensure_dir, normalize_path
)


class TestParseTime:
    def test_plain_seconds(self):
        assert parse_time("90") == 90.0
        assert parse_time("1.5") == 1.5
        assert parse_time("0") == 0.0

    def test_mm_ss(self):
        assert parse_time("1:30") == 90.0
        assert parse_time("0:05") == 5.0

    def test_mm_ss_ms(self):
        assert parse_time("1:30.5") == 90.5

    def test_hh_mm_ss(self):
        assert parse_time("1:02:30") == 3750.0
        assert parse_time("0:00:01") == 1.0

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_time("")

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_time("abc")


class TestFormatDuration:
    def test_zero(self):
        assert format_duration(0) == "0:00.000"

    def test_seconds(self):
        result = format_duration(90.5)
        assert "1:30.500" in result

    def test_hours(self):
        result = format_duration(3750.0)
        assert "1:02:30.000" in result

    def test_negative_clamped(self):
        result = format_duration(-5)
        assert "0:00.000" in result


class TestTempDir:
    def test_creates_and_cleans(self):
        with temp_dir(prefix="test-") as d:
            assert os.path.isdir(d)
            # Create a file inside
            fpath = os.path.join(d, "test.txt")
            with open(fpath, "w") as f:
                f.write("hello")
            assert os.path.exists(fpath)
        # After context exit, dir should be gone
        assert not os.path.exists(d)

    def test_keep(self):
        kept_path = None
        with temp_dir(prefix="test-keep-", keep=True) as d:
            kept_path = d
            fpath = os.path.join(d, "test.txt")
            with open(fpath, "w") as f:
                f.write("hello")
        # Dir should still exist
        assert os.path.exists(kept_path)
        # Clean up manually
        import shutil
        shutil.rmtree(kept_path)


class TestTempFilename:
    def test_generates_unique_name(self):
        with temp_dir(prefix="test-tmpfn-") as d:
            f1 = temp_filename("norm", "mp4", d)
            f2 = temp_filename("norm", "mp4", d)
            assert f1 != f2
            assert f1.endswith(".mp4")
            assert os.path.basename(f1).startswith("norm_")
            assert os.path.dirname(f1) == d


class TestEnsureDir:
    def test_creates_directory(self, tmp_path):
        new_dir = str(tmp_path / "new" / "subdir")
        result = ensure_dir(new_dir)
        assert os.path.isdir(result)
        assert result == new_dir

    def test_existing_ok(self):
        ensure_dir("/tmp")  # should not raise


class TestNormalizePath:
    def test_forward_slashes(self):
        result = normalize_path(r"C:\Users\test\file.mp4")
        assert "\\" not in result
        assert result.startswith("C:/")

    def test_home_expansion(self):
        result = normalize_path("~/videos/clip.mp4")
        assert not result.startswith("~")
        assert result.endswith("/videos/clip.mp4")
