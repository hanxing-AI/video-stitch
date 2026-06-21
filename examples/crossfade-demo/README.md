# Crossfade Demo

Stitch three clips with a 0.5-second crossfade transition between each,
plus fade-in at the start and fade-out at the end.

```bash
video-stitch -o crossfade-demo.mp4 \
  --crossfade 0.5 \
  --fade-in 1.0 \
  --fade-out 1.5 \
  clip1.mp4 clip2.mp4 clip3.mp4
```

Preview first:
```bash
video-stitch --dry-run -o crossfade-demo.mp4 \
  --crossfade 0.5 --fade-in 1.0 --fade-out 1.5 \
  clip1.mp4 clip2.mp4 clip3.mp4
```
