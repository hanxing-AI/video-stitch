"""Thin builder for constructing and running ffmpeg commands.

Not a general-purpose ffmpeg library — only the subset of flags
that video-stitch actually needs.
"""

import subprocess
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger("video_stitch")


class FFmpegCommand:
    """Builder for a single ffmpeg invocation."""

    def __init__(self):
        self._inputs: List[Dict[str, Any]] = []
        self._outputs: List[Dict[str, Any]] = []
        self._filter_complex: Optional[str] = None
        self._boolean_flags: List[str] = []
        self._global_opts: Dict[str, str] = {}
        self._map_cmds: List[str] = []

    def add_input(self, path: str, **opts) -> "FFmpegCommand":
        """Add an input file with optional flags.

        Common opts: ss (seek start), t (duration), to (stop time)
        """
        self._inputs.append({"path": path, "opts": opts})
        return self

    def add_output(self, path: str, **opts) -> "FFmpegCommand":
        """Add an output file with optional flags.

        Common opts: c:v (video codec), c:a (audio codec),
                     preset, crf, pix_fmt, movflags, etc.
        """
        self._outputs.append({"path": path, "opts": opts})
        return self

    def set_filter_complex(self, graph: str) -> "FFmpegCommand":
        """Set the -filter_complex filter graph string."""
        self._filter_complex = graph
        return self

    def add_map(self, mapping: str) -> "FFmpegCommand":
        """Add a -map argument (e.g., '[v]', '[a]', '0:v')."""
        self._map_cmds.append(mapping)
        return self

    def set_boolean(self, flag: str) -> "FFmpegCommand":
        """Add a boolean flag (no value), e.g., '-y'.

        Args:
            flag: Flag name WITHOUT leading dash, e.g., 'y'.
        """
        self._boolean_flags.append(flag)
        return self

    def set_global(self, key: str, value: str) -> "FFmpegCommand":
        """Set a global option with a value (e.g., -progress pipe:1)."""
        self._global_opts[key] = value
        return self

    def build(self) -> List[str]:
        """Build the complete ffmpeg argument list.

        Returns:
            List of strings ready for subprocess.run().
        """
        args = ["ffmpeg"]

        # Boolean flags (e.g., -y)
        for flag in self._boolean_flags:
            args.append(f"-{flag}")

        # Global options with values
        for k, v in self._global_opts.items():
            args.extend([f"-{k}", v])

        # Inputs
        for inp in self._inputs:
            for k, v in inp["opts"].items():
                args.extend([f"-{k}", str(v)])
            args.extend(["-i", inp["path"]])

        # Filter complex
        if self._filter_complex:
            args.extend(["-filter_complex", self._filter_complex])

        # Maps
        for m in self._map_cmds:
            args.extend(["-map", m])

        # Outputs
        for out in self._outputs:
            for k, v in out["opts"].items():
                args.extend([f"-{k}", str(v)])
            args.append(out["path"])

        return args

    def run(self, dry_run: bool = False, verbose: bool = False,
            capture: bool = True) -> subprocess.CompletedProcess:
        """Build and execute the ffmpeg command.

        Args:
            dry_run: Print command without executing.
            verbose: Print the command before running.
            capture: Capture stdout/stderr.

        Returns:
            subprocess.CompletedProcess.

        Raises:
            subprocess.CalledProcessError: If ffmpeg fails.
        """
        args = self.build()
        cmd_str = " ".join(args)

        if dry_run:
            logger.info(f"[DRY RUN] {cmd_str}")
            return subprocess.CompletedProcess(args, 0, stdout=b"", stderr=b"")

        if verbose:
            logger.info(f"Running: {cmd_str}")

        try:
            result = subprocess.run(
                args,
                capture_output=capture,
                text=True,
                check=True,
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg failed with code {e.returncode}")
            if e.stderr:
                stderr_lines = e.stderr.strip().split("\n")
                relevant = stderr_lines[-15:]
                logger.error(
                    "ffmpeg stderr (last 15 lines):\n" + "\n".join(relevant)
                )
            raise


def simple_command(inputs: List[str], output: str,
                   video_codec: str = "libx264",
                   audio_codec: str = "aac",
                   preset: str = "medium",
                   crf: int = 23,
                   pix_fmt: str = "yuv420p",
                   movflags: str = "+faststart",
                   extra_input_opts: Optional[Dict[str, str]] = None,
                   extra_output_opts: Optional[Dict[str, str]] = None,
                   overwrite: bool = True) -> FFmpegCommand:
    """Create a simple concatenation command (no filter graph).

    For simple concat without transitions, uses the concat demuxer approach.
    For more complex operations, use FFmpegCommand directly.
    """
    cmd = FFmpegCommand()

    if overwrite:
        cmd.set_boolean("y")

    for inp in inputs:
        opts = extra_input_opts.copy() if extra_input_opts else {}
        cmd.add_input(inp, **opts)

    output_opts = {
        "c:v": video_codec,
        "c:a": audio_codec,
        "preset": preset,
        "crf": str(crf),
        "pix_fmt": pix_fmt,
        "movflags": movflags,
    }
    if extra_output_opts:
        output_opts.update(extra_output_opts)

    cmd.add_output(output, **output_opts)
    return cmd
