# Changelog

## [1.0.0] — 2026-06-21

### Added
- Initial release
- Video concatenation with simple concat or xfade crossfade transitions
- Auto-normalization for mixed resolutions, framerates, and codecs
- Per-segment trimming with start/end/duration specifications
- Title card overlay (centered, timed text)
- Watermark overlay (persistent, positionable text)
- Fade in/out at video boundaries
- JSON recipe files for repeatable, version-controlled configurations
- `--probe` / `video-probe` command for video metadata inspection
- `--dry-run` mode to preview ffmpeg commands
- `--verbose` mode for detailed progress
- `--keep-temp` for debugging intermediate files
- System font auto-detection on Windows / macOS / Linux
- Crossfade type: "fade" and "fadeblack"
- Automated test suite with synthetic video generation (123 tests)
- Cross-platform: Windows, macOS, Linux
- Zero Python dependencies (ffmpeg only external requirement)
