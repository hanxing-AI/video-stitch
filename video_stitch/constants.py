"""All default values, encoder presets, and magic constants."""

# --- Normalization defaults ---
DEFAULT_RESOLUTION = (1920, 1080)
DEFAULT_FPS = 30
DEFAULT_VIDEO_CODEC = "libx264"
DEFAULT_CRF = 23
DEFAULT_PRESET = "medium"
DEFAULT_PIX_FMT = "yuv420p"
DEFAULT_AUDIO_CODEC = "aac"
DEFAULT_AUDIO_BITRATE = "192k"
DEFAULT_SAMPLE_RATE = 48000
DEFAULT_CHANNEL_LAYOUT = "stereo"

# Higher quality for intermediate (normalized) files
INTERMEDIATE_CRF = 18
INTERMEDIATE_PRESET = "fast"

# --- Transition defaults ---
DEFAULT_CROSSFADE_DURATION = 0.0  # no crossfade by default (simple concat)
DEFAULT_FADE_DURATION = 0.0       # no fade in/out by default

# --- Text overlay defaults ---
DEFAULT_FONT_SIZE = 48
DEFAULT_FONT_COLOR = "white"
DEFAULT_BORDER_COLOR = "black@0.5"
DEFAULT_BORDER_WIDTH = 2
DEFAULT_TITLE_DURATION = 3.0

# --- Supported formats ---
SUPPORTED_CONTAINERS = {"mp4", "webm", "mkv", "mov"}
SUPPORTED_TRANSITIONS = {"crossfade", "fadeblack"}

# --- Preset options ---
PRESET_OPTIONS = {"fast", "medium", "slow", "veryslow", "ultrafast", "slower"}

# --- Watermark position expressions (ffmpeg drawtext x:y) ---
WATERMARK_POSITIONS = {
    "bottom-right": "main_w-text_w-20:main_h-text_h-20",
    "bottom-left":  "20:main_h-text_h-20",
    "top-right":    "main_w-text_w-20:20",
    "top-left":     "20:20",
    "center":       "(main_w-text_w)/2:(main_h-text_h)/2",
}

# --- Minimum ffmpeg version required ---
MIN_FFMPEG_MAJOR = 4
MIN_FFMPEG_MINOR = 3
