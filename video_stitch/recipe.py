"""JSON recipe loader and validator for repeatable stitch configurations."""

import json
import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger("video_stitch")

# Current recipe schema version
SCHEMA_VERSION = "1.0"


@dataclass
class RecipeInput:
    """A single input in a recipe."""
    file: str
    trim: Optional[dict] = None  # {"start": float, "end": float} or {"start": float, "duration": float}
    label: Optional[str] = None


@dataclass
class RecipeNormalize:
    """Normalization settings in a recipe."""
    enabled: bool = True
    resolution: str = "1920x1080"
    fps: float = 30.0


@dataclass
class RecipeTransitions:
    """Transition settings in a recipe."""
    crossfade: float = 0.0
    type: str = "crossfade"


@dataclass
class RecipeEffects:
    """Edge effects in a recipe."""
    fade_in: float = 0.0
    fade_out: float = 0.0


@dataclass
class RecipeOverlay:
    """Text overlay definition in a recipe."""
    type: str  # "title" or "watermark"
    text: str
    duration: float = 3.0      # for title
    font_size: int = 48
    position: str = "bottom-right"  # for watermark


@dataclass
class RecipeOutput:
    """Output settings in a recipe."""
    file: str = "output.mp4"
    format: str = "mp4"
    preset: str = "medium"
    crf: int = 23


@dataclass
class Recipe:
    """Complete recipe for a video stitching operation."""
    version: str = SCHEMA_VERSION
    metadata: dict = field(default_factory=dict)
    inputs: List[RecipeInput] = field(default_factory=list)
    normalize: Optional[RecipeNormalize] = None
    transitions: Optional[RecipeTransitions] = None
    effects: Optional[RecipeEffects] = None
    overlays: List[RecipeOverlay] = field(default_factory=list)
    output: RecipeOutput = field(default_factory=RecipeOutput)


def load_recipe(path: str) -> Recipe:
    """Load and parse a recipe JSON file.

    Args:
        path: Path to the recipe JSON file.

    Returns:
        Parsed Recipe object.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the JSON is invalid or the recipe fails validation.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Recipe file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in recipe file '{path}': {e}")

    recipe = _parse_recipe_dict(data)
    errors = validate_recipe(recipe)
    if errors:
        raise ValueError(
            f"Invalid recipe '{path}':\n  " + "\n  ".join(errors)
        )

    return recipe


def validate_recipe(recipe: Recipe) -> list:
    """Validate a recipe. Returns list of error strings (empty = valid)."""
    errors = []

    if not recipe.inputs:
        errors.append("At least one input is required")

    for i, inp in enumerate(recipe.inputs):
        if not inp.file:
            errors.append(f"Input [{i}]: 'file' is required")
        elif not os.path.exists(inp.file):
            errors.append(f"Input [{i}]: file not found: {inp.file}")

        if inp.trim:
            if "start" not in inp.trim:
                errors.append(f"Input [{i}]: trim requires 'start'")
            else:
                start = inp.trim["start"]
                if not isinstance(start, (int, float)) or start < 0:
                    errors.append(f"Input [{i}]: trim.start must be >= 0")

            if "end" in inp.trim:
                end = inp.trim["end"]
                if not isinstance(end, (int, float)):
                    errors.append(f"Input [{i}]: trim.end must be a number")
                elif "start" in inp.trim and end <= inp.trim["start"]:
                    errors.append(f"Input [{i}]: trim.end must be > trim.start")
            elif "duration" in inp.trim:
                dur = inp.trim["duration"]
                if not isinstance(dur, (int, float)) or dur <= 0:
                    errors.append(f"Input [{i}]: trim.duration must be > 0")

    if recipe.output:
        from .constants import SUPPORTED_CONTAINERS
        if recipe.output.format not in SUPPORTED_CONTAINERS:
            errors.append(
                f"Output format '{recipe.output.format}' not supported. "
                f"Use: {', '.join(sorted(SUPPORTED_CONTAINERS))}"
            )
        if not (0 <= recipe.output.crf <= 51):
            errors.append(f"Output CRF must be 0-51: {recipe.output.crf}")

    if recipe.transitions:
        if recipe.transitions.crossfade < 0:
            errors.append("Transitions: crossfade cannot be negative")

    if recipe.effects:
        if recipe.effects.fade_in < 0:
            errors.append("Effects: fade_in cannot be negative")
        if recipe.effects.fade_out < 0:
            errors.append("Effects: fade_out cannot be negative")

    for i, ov in enumerate(recipe.overlays):
        if ov.type not in ("title", "watermark"):
            errors.append(f"Overlay [{i}]: type must be 'title' or 'watermark'")
        if not ov.text:
            errors.append(f"Overlay [{i}]: 'text' is required")

    return errors


def recipe_to_stitch_job(recipe: Recipe) -> dict:
    """Convert a Recipe to kwargs for StitchJob.

    Returns:
        dict of keyword arguments that can be unpacked into StitchJob().
    """
    from .trimmer import TrimSpec

    kwargs = {
        "inputs": [inp.file for inp in recipe.inputs],
        "output": recipe.output.file if recipe.output else "output.mp4",
    }

    # Trims
    trims = []
    for inp in recipe.inputs:
        if inp.trim:
            start = inp.trim.get("start", 0.0)
            end = inp.trim.get("end")
            duration = inp.trim.get("duration")
            trims.append(TrimSpec(start=start, end=end, duration=duration))
        else:
            trims.append(None)
    if any(t is not None for t in trims):
        kwargs["trims"] = trims

    # Normalize
    if recipe.normalize:
        kwargs["normalize"] = recipe.normalize.enabled
        if recipe.normalize.resolution:
            kwargs["target_resolution"] = recipe.normalize.resolution
        if recipe.normalize.fps:
            kwargs["target_fps"] = recipe.normalize.fps

    # Transitions
    if recipe.transitions:
        kwargs["crossfade"] = recipe.transitions.crossfade
        kwargs["transition_type"] = recipe.transitions.type

    # Effects
    if recipe.effects:
        kwargs["fade_in"] = recipe.effects.fade_in
        kwargs["fade_out"] = recipe.effects.fade_out

    # Overlays
    for ov in recipe.overlays:
        if ov.type == "title":
            kwargs["title_text"] = ov.text
            kwargs["title_duration"] = ov.duration
        elif ov.type == "watermark":
            kwargs["watermark_text"] = ov.text
            kwargs["watermark_position"] = ov.position

        if ov.font_size:
            kwargs["font_size"] = ov.font_size

    # Output
    if recipe.output:
        kwargs["output_format"] = recipe.output.format
        kwargs["preset"] = recipe.output.preset
        kwargs["crf"] = recipe.output.crf

    return kwargs


def _parse_recipe_dict(data: dict) -> Recipe:
    """Parse a raw JSON dict into a Recipe object."""
    recipe = Recipe()
    recipe.version = data.get("version", SCHEMA_VERSION)
    recipe.metadata = data.get("metadata", {})

    # Parse inputs
    for inp_data in data.get("inputs", []):
        inp = RecipeInput(
            file=inp_data.get("file", ""),
            trim=inp_data.get("trim"),
            label=inp_data.get("label"),
        )
        recipe.inputs.append(inp)

    # Parse normalize
    norm_data = data.get("normalize")
    if norm_data:
        recipe.normalize = RecipeNormalize(
            enabled=norm_data.get("enabled", True),
            resolution=norm_data.get("resolution", "1920x1080"),
            fps=norm_data.get("fps", 30.0),
        )

    # Parse transitions
    trans_data = data.get("transitions")
    if trans_data:
        recipe.transitions = RecipeTransitions(
            crossfade=trans_data.get("crossfade", 0.0),
            type=trans_data.get("type", "crossfade"),
        )

    # Parse effects
    effects_data = data.get("effects")
    if effects_data:
        recipe.effects = RecipeEffects(
            fade_in=effects_data.get("fade_in", 0.0),
            fade_out=effects_data.get("fade_out", 0.0),
        )

    # Parse overlays
    for ov_data in data.get("overlays", []):
        ov = RecipeOverlay(
            type=ov_data.get("type", "title"),
            text=ov_data.get("text", ""),
            duration=ov_data.get("duration", 3.0),
            font_size=ov_data.get("font_size", 48),
            position=ov_data.get("position", "bottom-right"),
        )
        recipe.overlays.append(ov)

    # Parse output
    out_data = data.get("output", {})
    recipe.output = RecipeOutput(
        file=out_data.get("file", "output.mp4"),
        format=out_data.get("format", "mp4"),
        preset=out_data.get("preset", "medium"),
        crf=out_data.get("crf", 23),
    )

    return recipe
