#!/usr/bin/env bash
# Install video-stitch from the repository root
set -e

echo "Installing video-stitch..."
pip install -e ".[dev]"

echo ""
echo "Installation complete. Verify with:"
echo "  video-stitch --version"
echo "  video-stitch --help"
echo "  video-probe --help"
echo ""
echo "Run tests:"
echo "  pytest -v"
