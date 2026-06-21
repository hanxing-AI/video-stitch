# ffmpeg Filters Used by video-stitch

Quick reference for the ffmpeg filters this tool relies on.

## xfade

Cross-fade transition between two video streams.

```
xfade=transition=fade:duration=0.5:offset=2.5
```

- `transition`: Effect type. video-stitch uses `fade` and `fadeblack`.
- `duration`: How long the transition lasts.
- `offset`: When the transition starts (seconds from the beginning).

Requires ffmpeg >= 4.3.

## acrossfade

Cross-fade transition between two audio streams.

```
acrossfade=d=0.5:c1=tri:c2=tri
```

- `d`: Duration of the crossfade.
- `c1`, `c2`: Fade curves for first/second stream. video-stitch uses `tri` (triangular).

## concat

Simple stream concatenation (no transitions). Used when `--crossfade 0`.

```
[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]
```

## fade / afade

Fade video/audio in or out.

```
fade=t=in:d=1.0                           # Fade in from black
fade=t=out:d=1.5:st=8.0                   # Fade out to black, starting at 8s
afade=t=in:d=1.0                          # Audio fade in
afade=t=out:d=1.5:st=8.0                  # Audio fade out
```

## drawtext

Draw text on video frames (used for title cards and watermarks).

```
drawtext=text='My Title':fontsize=72:fontcolor=white:
  x=(w-text_w)/2:y=(h-text_h)/2:
  enable='between(t,0,3)':
  bordercolor=black@0.5:borderw=2
```

Key parameters:
- `text`: The text to draw (must be escaped).
- `fontsize`: Font size in pixels.
- `fontcolor`: Color name, hex, or with alpha (`@` notation).
- `x`, `y`: Position expressions. `main_w` = video width, `text_w` = text width.
- `enable`: When to show the text. `between(t,start,end)` is most common.
- `fontfile`: Path to a .ttf/.otf file (optional on systems with fontconfig).
- `bordercolor`, `borderw`: Text outline for readability.

## scale + pad

Resize and letterbox/pillarbox video to target dimensions.

```
scale=1920:1080:force_original_aspect_ratio=decrease
pad=1920:1080:(ow-iw)/2:(oh-ih)/2
```

- `force_original_aspect_ratio=decrease`: Scale down to fit, never upscale/stretch.
- `pad`: Fill to exact dimensions with black bars, centered.

This preserves aspect ratio — no stretching, no cropping.

## format

Set pixel format.

```
format=yuv420p
```

yuv420p is the most compatible format for web/mobile playback.

## setpts / asetpts

Reset timestamps so each segment starts at 0:00.

```
setpts=PTS-STARTPTS
asetpts=PTS-STARTPTS
```

## aformat

Standardize audio format.

```
aformat=sample_rates=48000:channel_layouts=stereo
```
