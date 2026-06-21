"""Tests for pipeline.py."""

from video_stitch.pipeline import FFmpegCommand, simple_command


class TestFFmpegCommand:
    def test_basic_command(self):
        cmd = FFmpegCommand()
        cmd.add_input("input.mp4")
        cmd.add_output("output.mp4", **{"c:v": "libx264"})
        args = cmd.build()

        assert args[0] == "ffmpeg"
        assert "-i" in args
        assert "input.mp4" in args
        assert "output.mp4" in args
        assert "-c:v" in args
        assert "libx264" in args

    def test_with_filter_complex(self):
        cmd = FFmpegCommand()
        cmd.set_global("y", "")
        cmd.add_input("a.mp4")
        cmd.add_input("b.mp4")
        cmd.set_filter_complex("[0:v][1:v]xfade=transition=fade:duration=0.5[v]")
        cmd.add_map("[v]")
        cmd.add_output("out.mp4", **{"c:v": "libx264"})
        args = cmd.build()

        assert "-y" in args
        assert "-filter_complex" in args
        assert "[0:v][1:v]xfade" in args[args.index("-filter_complex") + 1]
        assert "-map" in args
        assert "[v]" in args

    def test_input_with_options(self):
        cmd = FFmpegCommand()
        cmd.add_input("clip.mp4", ss="10.5", t="30")
        args = cmd.build()

        # -ss and -t should come before -i
        ss_idx = args.index("-ss")
        t_idx = args.index("-t")
        i_idx = args.index("-i")
        assert ss_idx < i_idx
        assert t_idx < i_idx
        assert args[ss_idx + 1] == "10.5"
        assert args[t_idx + 1] == "30"

    def test_multiple_outputs(self):
        cmd = FFmpegCommand()
        cmd.add_input("in.mp4")
        cmd.add_output("out1.mp4", **{"c:v": "libx264"})
        cmd.add_output("out2.mp4", **{"c:v": "libx265"})
        args = cmd.build()

        assert args.count("-c:v") == 2

    def test_dry_run(self):
        cmd = FFmpegCommand()
        cmd.add_input("in.mp4")
        cmd.add_output("out.mp4")
        result = cmd.run(dry_run=True)
        assert result.returncode == 0


class TestSimpleCommand:
    def test_creates_valid_command(self):
        cmd = simple_command(["a.mp4", "b.mp4"], "out.mp4")
        args = cmd.build()
        assert args[0] == "ffmpeg"
        assert "a.mp4" in args
        assert "b.mp4" in args
        assert "out.mp4" in args
        assert "-c:v" in args
        assert "libx264" in args

    def test_overwrite_flag(self):
        cmd = simple_command(["a.mp4"], "out.mp4")
        args = cmd.build()
        assert "-y" in args
