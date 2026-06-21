"""Tests for stitcher.py — the main orchestrator."""

import os
import pytest
from video_stitch.stitcher import StitchJob, run
from video_stitch.probe import probe


class TestStitchJob:
    def test_defaults(self):
        job = StitchJob(inputs=["a.mp4"], output="out.mp4")
        assert job.output_format == "mp4"
        assert job.preset == "medium"
        assert job.crf == 23

    def test_validate_empty_inputs(self):
        job = StitchJob(inputs=[], output="out.mp4")
        errors = job.validate()
        assert len(errors) > 0

    def test_validate_bad_format(self):
        job = StitchJob(inputs=["a.mp4"], output="out.avi", output_format="avi")
        errors = job.validate()
        assert len(errors) > 0

    def test_validate_bad_crf(self):
        job = StitchJob(inputs=["a.mp4"], crf=100)
        errors = job.validate()
        assert len(errors) > 0

    def test_validate_ok(self):
        job = StitchJob(inputs=["a.mp4", "b.mp4"])
        assert job.validate() == []

    def test_validate_bad_resolution(self):
        job = StitchJob(inputs=["a.mp4"], target_resolution="bad")
        errors = job.validate()
        assert len(errors) > 0


class TestRunBasic:
    """Integration tests that actually stitch videos."""

    def test_simple_concat_two_videos(self, sample_video_1080p, tmp_path):
        """Concatenate two identical 1080p videos."""
        out = str(tmp_path / "output.mp4")
        job = StitchJob(
            inputs=[sample_video_1080p, sample_video_1080p],
            output=out,
            normalize=False,  # Same resolution, skip normalization
            verbose=False,
        )
        result = run(job)
        assert result == out
        assert os.path.exists(out)

        # Verify output
        info = probe(out)
        assert info.primary_video.width == 1920
        assert info.primary_video.height == 1080
        # Duration should be approximately 3+3 = 6s (no transitions)
        assert 5.5 < info.duration < 6.5

    def test_simple_concat_three_videos(self, three_matching_videos, tmp_path):
        """Concatenate three identical videos."""
        out = str(tmp_path / "output_three.mp4")
        job = StitchJob(
            inputs=three_matching_videos,
            output=out,
            normalize=False,
            verbose=False,
        )
        result = run(job)
        assert os.path.exists(out)
        info = probe(out)
        # ~9 seconds
        assert 8.0 < info.duration < 10.0

    def test_with_crossfade(self, sample_video_1080p, tmp_path):
        """Concatenate two videos with a crossfade transition."""
        out = str(tmp_path / "output_xfade.mp4")
        job = StitchJob(
            inputs=[sample_video_1080p, sample_video_1080p],
            output=out,
            crossfade=0.5,
            normalize=False,
            verbose=False,
        )
        result = run(job)
        assert os.path.exists(out)
        info = probe(out)
        # Duration: 3+3-0.5 = 5.5s
        assert 5.0 < info.duration < 6.0

    def test_with_fades(self, sample_video_1080p, tmp_path):
        """Single video with fade in/out."""
        out = str(tmp_path / "output_fades.mp4")
        job = StitchJob(
            inputs=[sample_video_1080p],
            output=out,
            fade_in=0.5,
            fade_out=0.5,
            normalize=False,
            verbose=False,
        )
        result = run(job)
        assert os.path.exists(out)

    def test_with_title(self, sample_video_1080p, tmp_path):
        """Single video with title card overlay."""
        out = str(tmp_path / "output_title.mp4")
        job = StitchJob(
            inputs=[sample_video_1080p],
            output=out,
            title_text="Test Title",
            title_duration=2.0,
            normalize=False,
            verbose=False,
        )
        result = run(job)
        assert os.path.exists(out)

    def test_with_watermark(self, sample_video_1080p, tmp_path):
        """Single video with watermark."""
        out = str(tmp_path / "output_wm.mp4")
        job = StitchJob(
            inputs=[sample_video_1080p],
            output=out,
            watermark_text="(c) Test",
            normalize=False,
            verbose=False,
        )
        result = run(job)
        assert os.path.exists(out)

    def test_dry_run(self, sample_video_1080p, tmp_path):
        """Dry run should not create output."""
        out = str(tmp_path / "output_dry.mp4")
        job = StitchJob(
            inputs=[sample_video_1080p],
            output=out,
            dry_run=True,
        )
        result = run(job)
        assert not os.path.exists(out)

    def test_missing_input_raises(self, tmp_path):
        """Non-existent input should raise FileNotFoundError."""
        out = str(tmp_path / "out.mp4")
        job = StitchJob(
            inputs=["nonexistent.mp4"],
            output=out,
        )
        with pytest.raises(FileNotFoundError):
            run(job)

    def test_invalid_job_raises(self):
        """Invalid job should raise ValueError."""
        job = StitchJob(inputs=[], output="out.mp4")
        with pytest.raises(ValueError):
            run(job)

    def test_normalize_mixed_resolutions(self, sample_video_1080p,
                                         sample_video_720p, tmp_path):
        """Stitch videos of different resolutions with normalization."""
        out = str(tmp_path / "output_norm.mp4")
        job = StitchJob(
            inputs=[sample_video_1080p, sample_video_720p],
            output=out,
            target_resolution="1920x1080",
            normalize=True,
            verbose=False,
        )
        result = run(job)
        assert os.path.exists(out)
        info = probe(out)
        assert info.primary_video.width == 1920
        assert info.primary_video.height == 1080
