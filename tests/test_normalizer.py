"""Tests for normalizer.py."""

import os
import pytest
from video_stitch.normalizer import (
    NormalizeConfig, normalize, needs_normalization,
    any_needs_normalization, normalize_all,
)
from video_stitch.probe import probe


class TestNormalizeConfig:
    def test_defaults(self):
        config = NormalizeConfig()
        assert config.width == 1920
        assert config.height == 1080
        assert config.fps == 30
        assert config.video_codec == "libx264"

    def test_custom(self):
        config = NormalizeConfig(width=1280, height=720, fps=24)
        assert config.width == 1280
        assert config.height == 720
        assert config.fps == 24


class TestNormalize:
    def test_normalize_1080p_to_1080p(self, sample_video_1080p, tmp_path):
        """Normalizing a 1080p video to 1080p should work fine."""
        out = str(tmp_path / "norm.mp4")
        config = NormalizeConfig(width=1920, height=1080, fps=30)
        result = normalize(sample_video_1080p, out, config)
        assert result == out
        assert os.path.exists(out)
        assert os.path.getsize(out) > 0

    def test_normalize_720p_to_1080p(self, sample_video_720p, tmp_path):
        """720p -> 1080p: should upscale with letterbox."""
        out = str(tmp_path / "norm_720to1080.mp4")
        config = NormalizeConfig(width=1920, height=1080, fps=30)
        result = normalize(sample_video_720p, out, config)

        # Verify output
        info = probe(out)
        assert info.primary_video.width == 1920
        assert info.primary_video.height == 1080

    def test_normalize_4k_to_1080p(self, sample_video_4k, tmp_path):
        """4K -> 1080p: should downscale."""
        out = str(tmp_path / "norm_4kto1080.mp4")
        config = NormalizeConfig(width=1920, height=1080, fps=30)
        result = normalize(sample_video_4k, out, config)

        info = probe(out)
        assert info.primary_video.width == 1920
        assert info.primary_video.height == 1080

    def test_normalize_no_audio_input(self, sample_video_no_audio, tmp_path):
        """Normalizing a video without audio should still work."""
        out = str(tmp_path / "norm_noaudio.mp4")
        config = NormalizeConfig()
        result = normalize(sample_video_no_audio, out, config)
        assert os.path.exists(out)

    def test_dry_run(self, sample_video_1080p, tmp_path):
        out = str(tmp_path / "norm_dry.mp4")
        config = NormalizeConfig()
        normalize(sample_video_1080p, out, config, dry_run=True)
        # File should not be created in dry_run mode
        assert not os.path.exists(out)


class TestNeedsNormalization:
    def test_matching_does_not_need(self, sample_video_1080p):
        info = probe(sample_video_1080p)
        config = NormalizeConfig(width=1920, height=1080, fps=30)
        # Note: pix_fmt from testsrc is yuv420p, matches default
        assert not needs_normalization(info, config)

    def test_different_resolution_needs(self, sample_video_720p):
        info = probe(sample_video_720p)
        config = NormalizeConfig(width=1920, height=1080, fps=30)
        assert needs_normalization(info, config)

    def test_different_fps_needs(self, sample_video_1080p):
        info = probe(sample_video_1080p)
        config = NormalizeConfig(width=1920, height=1080, fps=60)
        assert needs_normalization(info, config)


class TestAnyNeedsNormalization:
    def test_all_matching(self, sample_video_1080p):
        # Both are 1080p30 — same file used twice as example
        config = NormalizeConfig(width=1920, height=1080, fps=30, pix_fmt="yuv420p")
        result = any_needs_normalization(
            [sample_video_1080p, sample_video_1080p], config
        )
        assert not result

    def test_mixed_needs(self, sample_video_1080p, sample_video_720p):
        config = NormalizeConfig(width=1920, height=1080, fps=30)
        result = any_needs_normalization(
            [sample_video_1080p, sample_video_720p], config
        )
        assert result


class TestNormalizeAll:
    def test_normalizes_mixed(self, sample_video_1080p, sample_video_720p, tmp_path):
        out_dir = str(tmp_path / "norm")
        os.makedirs(out_dir)
        config = NormalizeConfig(width=1920, height=1080, fps=30)
        results = normalize_all(
            [sample_video_1080p, sample_video_720p],
            out_dir, config
        )
        assert len(results) == 2
        for r in results:
            assert os.path.exists(r)
            info = probe(r)
            assert info.primary_video.width == 1920
            assert info.primary_video.height == 1080
