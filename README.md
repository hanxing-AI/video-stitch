# video-stitch

> Stitch videos together with transitions, text, and effects.
> A lightweight ffmpeg wrapper with zero Python dependencies.

**video-stitch** lets you concatenate multiple video clips with crossfade
transitions, auto-normalize mixed resolutions, trim segments, overlay title
cards and watermarks — all from the command line or a JSON recipe file.

## Quick Start

```bash
# Install
pip install video-stitch

# Stitch three clips
video-stitch -o final.mp4 clip1.mp4 clip2.mp4 clip3.mp4

# With crossfade and fade in/out
video-stitch -o final.mp4 --crossfade 0.5 --fade-in 1 --fade-out 1.5 *.mp4

# Add title and watermark
video-stitch -o final.mp4 --title "My Lecture" --watermark "(c) 2026" *.mp4

# Auto-normalize mixed resolutions
video-stitch -o final.mp4 --target-resolution 1920x1080 *.mp4

# Use a recipe file
video-stitch --recipe my-project.json

# Preview without executing
video-stitch --dry-run -o final.mp4 --crossfade 0.5 *.mp4

# Probe video info
video-stitch --probe clip1.mp4
```

## Requirements

- **Python** >= 3.9
- **ffmpeg** >= 4.3 (must have `xfade` filter)
- That's it. No other dependencies.

Check your environment:
```bash
bash scripts/check-deps.sh
```

## Features

- **Concatenate** multiple videos with optional crossfade transitions
- **Auto-normalize** mixed resolutions, framerates, and codecs
- **Trim** segments with start/end times
- **Title cards** and **watermarks** via drawtext
- **Fade in/out** at video boundaries
- **JSON recipe files** for repeatable, version-controlled configurations
- **Dry-run mode** to preview ffmpeg commands before execution
- **Probe mode** for quick video metadata inspection

## Recipe Files

For repeatable projects, save your configuration as JSON:

```json
{
  "version": "1.0",
  "metadata": { "title": "Lecture Highlights" },
  "inputs": [
    { "file": "intro.mp4", "trim": { "start": 0, "end": 30 }, "label": "Intro" },
    { "file": "main.mp4", "label": "Main" }
  ],
  "normalize": { "enabled": true, "resolution": "1920x1080", "fps": 30 },
  "transitions": { "crossfade": 0.5 },
  "effects": { "fade_in": 1.0, "fade_out": 1.5 },
  "overlays": [
    { "type": "title", "text": "Aesthetics 101", "duration": 3.0 },
    { "type": "watermark", "text": "(c) 2026" }
  ],
  "output": { "file": "lecture.mp4", "format": "mp4", "preset": "medium", "crf": 23 }
}
```

Run it:
```bash
video-stitch --recipe lecture.json
```

## Installation

### From PyPI (coming soon)
```bash
pip install video-stitch
```

### From source
```bash
git clone https://github.com/shuangyan/video-stitch.git
cd video-stitch
pip install -e .
```

### Verify
```bash
video-stitch --version
video-stitch --help
```

## Project Structure

```
video-stitch/
├── video_stitch/          # Python package
│   ├── cli.py             # Command-line interface
│   ├── stitcher.py        # Main orchestrator
│   ├── normalizer.py      # Resolution/codec normalization
│   ├── trimmer.py         # Video trimming
│   ├── transitions.py     # xfade filter graph builder
│   ├── overlay.py         # drawtext text overlays
│   ├── probe.py           # ffprobe metadata extraction
│   ├── recipe.py          # JSON recipe loader
│   ├── pipeline.py        # ffmpeg command builder
│   └── ...
├── scripts/               # Utility scripts
├── templates/             # Recipe templates
├── references/            # Reference docs
├── examples/              # Worked examples
└── tests/                 # Test suite
```

## License

MIT — see [LICENSE](LICENSE).

---

Made with ❤️ by Shuangyan & Luoxian.
