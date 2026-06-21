"""Shared test fixtures — generates synthetic test videos with ffmpeg."""

import os
import subprocess
import pytest


def _generate_test_video(path: str, duration: float = 3.0,
                         width: int = 1920, height: int = 1080,
                         fps: int = 30, with_audio: bool = True,
                         codec: str = "libx264"):
    """Generate a synthetic test video using ffmpeg's testsrc + sine filters.

    Creates a video with color bars pattern and optional 440Hz tone audio.
    """
    args = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"testsrc=duration={duration}:size={width}x{height}:rate={fps}",
    ]

    if with_audio:
        args.extend([
            "-f", "lavfi", "-i",
            f"sine=frequency=440:duration={duration}",
        ])

    args.extend([
        "-c:v", codec,
        "-pix_fmt", "yuv420p",
        "-preset", "ultrafast",
    ])

    if with_audio:
        args.extend([
            "-c:a", "aac", "-b:a", "128k",
            "-ar", "48000", "-ac", "2",
            "-shortest",
        ])

    args.append(path)

    subprocess.run(args, check=True, capture_output=True)
    return path


@pytest.fixture
def sample_video_1080p(tmp_path):
    """Generate a 3-second 1080p30 test video with audio."""
    path = str(tmp_path / "test_1080p.mp4")
    _generate_test_video(path, duration=3.0, width=1920, height=1080, fps=30)
    return path


@pytest.fixture
def sample_video_720p(tmp_path):
    """Generate a 3-second 720p30 test video with audio."""
    path = str(tmp_path / "test_720p.mp4")
    _generate_test_video(path, duration=3.0, width=1280, height=720, fps=30)
    return path


@pytest.fixture
def sample_video_4k(tmp_path):
    """Generate a 3-second 4K30 test video with audio."""
    path = str(tmp_path / "test_4k.mp4")
    _generate_test_video(path, duration=3.0, width=3840, height=2160, fps=30)
    return path


@pytest.fixture
def sample_video_no_audio(tmp_path):
    """Generate a 3-second 1080p30 test video WITHOUT audio."""
    path = str(tmp_path / "test_noaudio.mp4")
    _generate_test_video(path, duration=3.0, width=1920, height=1080,
                         fps=30, with_audio=False)
    return path


@pytest.fixture
def sample_video_short(tmp_path):
    """Generate a 1-second 1080p30 test video."""
    path = str(tmp_path / "test_short.mp4")
    _generate_test_video(path, duration=1.0, width=1920, height=1080, fps=30)
    return path


@pytest.fixture
def three_matching_videos(tmp_path):
    """Generate three identical 1080p30 3-second test videos."""
    paths = []
    for i in range(3):
        path = str(tmp_path / f"clip_{i}.mp4")
        _generate_test_video(path, duration=3.0, width=1920, height=1080, fps=30)
        paths.append(path)
    return paths


@pytest.fixture
def mixed_resolution_videos(tmp_path):
    """Generate videos of different resolutions."""
    paths = [
        str(tmp_path / "clip_1080p.mp4"),
        str(tmp_path / "clip_720p.mp4"),
        str(tmp_path / "clip_4k.mp4"),
    ]
    configs = [
        (3.0, 1920, 1080),
        (2.5, 1280, 720),
        (4.0, 3840, 2160),
    ]
    for path, (dur, w, h) in zip(paths, configs):
        _generate_test_video(path, duration=dur, width=w, height=h)
    return paths
