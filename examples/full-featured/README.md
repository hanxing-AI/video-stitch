# Full-Featured Example

This example uses everything: trim, normalization, crossfade, fades, title, and watermark.

First, copy the recipe template:
```bash
cp templates/recipe-full.json my-video.json
```

Edit `my-video.json` to point to your actual video files:
```json
"inputs": [
  { "file": "raw/intro.mp4", "trim": { "start": 0, "end": 15 } },
  { "file": "raw/main.mp4", "trim": { "start": 30, "duration": 60 } },
  { "file": "raw/closing.mp4" }
]
```

Run it:
```bash
video-stitch --recipe my-video.json --verbose
```

The recipe approach lets you:
- Save the configuration in version control
- Re-run anytime the source files change
- Share the recipe with others
