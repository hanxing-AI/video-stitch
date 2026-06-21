"""Tests for probe.py."""

import pytest
from video_stitch.probe import (
    probe, probe_json, probe_summary,
    FileInfo, VideoStream, AudioStream,
    compatible, find_common_params,
)


class TestProbe:
    def test_probe_1080p(self, sample_video_1080p):
        info = probe(sample_video_1080p)
        assert isinstance(info, FileInfo)
        assert info.has_video
        assert info.has_audio
        assert info.primary_video.width == 1920
        assert info.primary_video.height == 1080
        assert abs(info.primary_video.fps - 30.0) < 1.0
        assert info.duration > 0

    def test_probe_720p(self, sample_video_720p):
        info = probe(sample_video_720p)
        assert info.primary_video.width == 1280
        assert info.primary_video.height == 720

    def test_probe_4k(self, sample_video_4k):
        info = probe(sample_video_4k)
        assert info.primary_video.width == 3840
        assert info.primary_video.height == 2160

    def test_probe_no_audio(self, sample_video_no_audio):
        info = probe(sample_video_no_audio)
        assert info.has_video
        assert not info.has_audio

    def test_probe_nonexistent(self, tmp_path):
        fake = str(tmp_path / "nonexistent.mp4")
        with pytest.raises(FileNotFoundError):
            probe(fake)


class TestProbeJson:
    def test_returns_json_string(self, sample_video_1080p):
        result = probe_json(sample_video_1080p)
        assert isinstance(result, str)
        assert "streams" in result.lower() or '"streams"' in result


class TestProbeSummary:
    def test_returns_string(self, sample_video_1080p):
        summary = probe_summary(sample_video_1080p)
        assert isinstance(summary, str)
        assert "1920" in summary
        assert "1080" in summary


class TestCompatible:
    def test_same_videos_compatible(self, sample_video_1080p):
        # Same file should be compatible with itself
        a = probe(sample_video_1080p)
        assert compatible(a, a)

    def test_different_resolution_incompatible(self, sample_video_1080p, sample_video_720p):
        a = probe(sample_video_1080p)
        b = probe(sample_video_720p)
        assert not compatible(a, b)

    def test_no_video_incompatible(self, tmp_path):
        # FileInfo with no video streams
        a = FileInfo(path="test.mp4")
        b = FileInfo(path="test2.mp4")
        assert not compatible(a, b)


class TestFindCommonParams:
    def test_single_file(self, sample_video_1080p):
        info = probe(sample_video_1080p)
        params = find_common_params([info])
        assert params["width"] == 1920
        assert params["height"] == 1080

    def test_mixed_resolutions(self, sample_video_1080p, sample_video_720p):
        a = probe(sample_video_1080p)
        b = probe(sample_video_720p)
        params = find_common_params([a, b])
        # Should pick one of the resolutions (both appear once, first wins)
        assert params["width"] in (1920, 1280)

    def test_empty_list(self):
        params = find_common_params([])
        assert params["width"] == 1920
        assert params["height"] == 1080
