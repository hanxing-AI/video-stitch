# Troubleshooting

## Common Issues

### "xfade: First input link ... parameters do not match"

**Cause**: Input videos have different resolutions or pixel formats.

**Fix**: Enable normalization (enabled by default). Remove `--no-normalize` if you set it.

### "No such filter: 'xfade'"

**Cause**: ffmpeg version is older than 4.3.

**Fix**: Upgrade ffmpeg. Check version: `ffmpeg -version`

### Chinese/CJK text not showing or garbled

**Cause**: No Chinese font available for drawtext.

**Fix**: Use `--font-file` to specify a Chinese font:
```bash
video-stitch --font-file "C:/Windows/Fonts/msyh.ttf" --title "你好" -o out.mp4 clip.mp4
```

### "Fontconfig error: Cannot load default config file"

**Cause**: ffmpeg was built with fontconfig but no fontconfig configuration exists.
This is common on Windows.

**Fix**: video-stitch auto-detects Windows system fonts (arial.ttf, segoeui.ttf, calibri.ttf).
If this fails, use `--font-file` explicitly.

### Output has no audio

**Cause**: Some inputs may not have audio streams, or audio parameters differ.

**Fix**: 
1. Use `video-stitch --probe *.mp4` to check which files have audio.
2. Enable normalization to standardize audio formats.

### Trim times are wrong

**Cause**: Timestamp format confusion.

**Fix**: Use seconds (e.g., `90.5`) or MM:SS format (e.g., `1:30.5`). Check with `--dry-run`.

### Output file is very large

**Cause**: CRF value too low (lower = higher quality = bigger file).

**Fix**: Use default CRF 23, or try `--crf 28` for smaller files. Also try `--preset fast`.

### Crossfade produces black flash

**Cause**: xfade offset miscalculated, or crossfade duration exceeds a segment's length.

**Fix**: Reduce `--crossfade` duration, or ensure all segments are longer than the crossfade value.

### Audio/video out of sync after stitching

**Cause**: Input timestamps are inconsistent.

**Fix**: Ensure normalization is enabled (it's on by default). Normalization resets timestamps.

## Getting Help

1. First, run with `--verbose --dry-run` to see the exact ffmpeg commands
2. Copy the ffmpeg command and try running it directly to isolate the issue
3. Run `video-stitch --probe` on each input to verify metadata
4. Check that inputs aren't corrupted: `ffplay input.mp4`
