"""Tests for transitions.py."""

import pytest
from video_stitch.transitions import (
    TransitionConfig, compute_xfade_offsets,
    build_video_filter_graph, build_audio_filter_graph,
    total_output_duration,
)


class TestTransitionConfig:
    def test_defaults(self):
        c = TransitionConfig()
        assert c.crossfade_duration == 0.0
        assert c.fade_in_duration == 0.0
        assert c.fade_out_duration == 0.0
        assert c.transition_type == "crossfade"

    def test_custom(self):
        c = TransitionConfig(
            crossfade_duration=0.5,
            fade_in_duration=1.0,
            fade_out_duration=2.0,
        )
        assert c.crossfade_duration == 0.5

    def test_validate_crossfade_negative(self):
        c = TransitionConfig(crossfade_duration=-0.1)
        errors = c.validate()
        assert len(errors) > 0

    def test_validate_bad_type(self):
        c = TransitionConfig(transition_type="wipe")
        errors = c.validate()
        assert len(errors) > 0

    def test_validate_ok(self):
        c = TransitionConfig()
        assert c.validate() == []


class TestComputeXfadeOffsets:
    def test_no_crossfade(self):
        offsets = compute_xfade_offsets([3.0, 4.0, 5.0], 0.0)
        assert offsets == [0.0, 0.0]

    def test_basic(self):
        # 3 inputs: 3s, 4s, 5s with 0.5s crossfade
        # offset[0] = 3 - 0.5 = 2.5
        # offset[1] = (3+4) - 2*0.5 = 7-1 = 6.0
        offsets = compute_xfade_offsets([3.0, 4.0, 5.0], 0.5)
        assert offsets == [2.5, 6.0]

    def test_two_inputs(self):
        offsets = compute_xfade_offsets([5.0, 3.0], 1.0)
        assert offsets == [4.0]

    def test_crossfade_too_long(self):
        with pytest.raises(ValueError, match="shorter than"):
            compute_xfade_offsets([2.0, 3.0], 2.5)

    def test_single_input(self):
        # Single input has no transitions
        offsets = compute_xfade_offsets([5.0], 1.0)
        assert offsets == []


class TestBuildVideoFilterGraph:
    def test_single_input(self):
        graph = build_video_filter_graph(1, [5.0], TransitionConfig())
        assert "0:v" in graph

    def test_simple_concat(self):
        config = TransitionConfig(crossfade_duration=0.0)
        graph = build_video_filter_graph(3, [3.0, 3.0, 3.0], config)
        assert "concat" in graph
        assert "n=3" in graph

    def test_with_crossfade(self):
        config = TransitionConfig(crossfade_duration=0.5)
        graph = build_video_filter_graph(3, [3.0, 4.0, 5.0], config)
        assert "xfade" in graph
        assert "offset" in graph

    def test_with_fades(self):
        config = TransitionConfig(fade_in_duration=1.0, fade_out_duration=2.0)
        graph = build_video_filter_graph(1, [5.0], config)
        assert "fade=t=in" in graph
        assert "fade=t=out" in graph

    def test_empty_inputs_raises(self):
        with pytest.raises(ValueError):
            build_video_filter_graph(0, [], TransitionConfig())

    def test_mismatched_durations_raises(self):
        with pytest.raises(ValueError):
            build_video_filter_graph(3, [1.0], TransitionConfig())

    def test_invalid_config_raises(self):
        config = TransitionConfig(crossfade_duration=-1.0)
        with pytest.raises(ValueError):
            build_video_filter_graph(2, [3.0, 3.0], config)


class TestBuildAudioFilterGraph:
    def test_single_input(self):
        graph = build_audio_filter_graph(1, [5.0], TransitionConfig())
        assert "0:a" in graph

    def test_simple_concat(self):
        graph = build_audio_filter_graph(3, [3.0, 3.0, 3.0],
                                         TransitionConfig())
        assert "concat" in graph
        assert "a=1" in graph

    def test_with_crossfade(self):
        config = TransitionConfig(crossfade_duration=0.5)
        graph = build_audio_filter_graph(3, [3.0, 4.0, 5.0], config)
        assert "acrossfade" in graph

    def test_with_fades(self):
        config = TransitionConfig(fade_in_duration=1.0, fade_out_duration=2.0)
        graph = build_audio_filter_graph(1, [5.0], config)
        assert "afade=t=in" in graph
        assert "afade=t=out" in graph


class TestTotalOutputDuration:
    def test_no_transitions(self):
        d = total_output_duration([3.0, 4.0, 5.0], TransitionConfig())
        assert d == 12.0

    def test_with_crossfade(self):
        config = TransitionConfig(crossfade_duration=1.0)
        d = total_output_duration([3.0, 4.0, 5.0], config)
        assert d == 10.0  # 12 - 2*1

    def test_fades_dont_change_duration(self):
        config = TransitionConfig(fade_in_duration=1.0, fade_out_duration=2.0)
        d = total_output_duration([3.0, 4.0], config)
        assert d == 7.0  # Fades don't change duration
