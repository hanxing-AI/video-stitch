#!/usr/bin/env bash
# Check dependencies for video-stitch
set -e

echo "=== video-stitch dependency check ==="
echo ""

# Check Python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "ERROR: Python 3 not found. Install Python >= 3.9"
    exit 1
fi

PY_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
echo "Python: $PY_VERSION"

# Check ffmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "ERROR: ffmpeg not found. Install ffmpeg >= 4.3"
    exit 1
fi

FF_VERSION=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
echo "ffmpeg: $FF_VERSION"

# Check xfade filter support
if ! ffmpeg -filters 2>&1 | grep -q xfade; then
    echo "ERROR: ffmpeg does not have xfade filter (requires ffmpeg >= 4.3)"
    exit 1
fi
echo "xfade filter: available"

# Check drawtext filter support
if ffmpeg -filters 2>&1 | grep -q drawtext; then
    echo "drawtext filter: available"
else
    echo "WARNING: drawtext filter not available. Text overlays will not work."
fi

# Check ffprobe
if command -v ffprobe &>/dev/null; then
    echo "ffprobe: available"
else
    echo "WARNING: ffprobe not found. Probe feature will not work."
fi

echo ""
echo "All required dependencies are available."
echo "Install video-stitch: pip install -e ."
