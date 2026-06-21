"""Tests for recipe.py."""

import json
import pytest
from video_stitch.recipe import (
    Recipe, RecipeInput, RecipeNormalize, RecipeTransitions,
    RecipeEffects, RecipeOverlay, RecipeOutput,
    load_recipe, validate_recipe, recipe_to_stitch_job,
)


class TestValidateRecipe:
    def test_valid_minimal(self):
        recipe = Recipe(
            inputs=[RecipeInput(file="clip1.mp4")],
            output=RecipeOutput(file="out.mp4"),
        )
        # File doesn't exist, so validation will fail
        errors = validate_recipe(recipe)
        assert len(errors) > 0  # file not found

    def test_no_inputs(self):
        recipe = Recipe(inputs=[])
        errors = validate_recipe(recipe)
        assert any("At least one input" in e for e in errors)

    def test_bad_output_format(self):
        recipe = Recipe(
            inputs=[RecipeInput(file="clip1.mp4")],
            output=RecipeOutput(format="avi"),
        )
        errors = validate_recipe(recipe)
        assert any("format" in e.lower() for e in errors)

    def test_bad_crf(self):
        recipe = Recipe(
            inputs=[RecipeInput(file="clip1.mp4")],
            output=RecipeOutput(crf=100),
        )
        errors = validate_recipe(recipe)
        assert any("CRF" in e for e in errors)

    def test_bad_overlay_type(self):
        recipe = Recipe(
            inputs=[RecipeInput(file="clip1.mp4")],
            overlays=[RecipeOverlay(type="bad", text="x")],
        )
        errors = validate_recipe(recipe)
        assert any("type" in e.lower() for e in errors)


class TestRecipeToStitchJob:
    def test_minimal(self):
        recipe = Recipe(
            inputs=[RecipeInput(file="a.mp4"), RecipeInput(file="b.mp4")],
            output=RecipeOutput(file="out.mp4", format="mp4"),
        )
        kwargs = recipe_to_stitch_job(recipe)
        assert kwargs["inputs"] == ["a.mp4", "b.mp4"]
        assert kwargs["output"] == "out.mp4"

    def test_with_transitions(self):
        recipe = Recipe(
            inputs=[RecipeInput(file="a.mp4")],
            transitions=RecipeTransitions(crossfade=0.5, type="fadeblack"),
        )
        kwargs = recipe_to_stitch_job(recipe)
        assert kwargs["crossfade"] == 0.5
        assert kwargs["transition_type"] == "fadeblack"

    def test_with_effects(self):
        recipe = Recipe(
            inputs=[RecipeInput(file="a.mp4")],
            effects=RecipeEffects(fade_in=1.0, fade_out=2.0),
        )
        kwargs = recipe_to_stitch_job(recipe)
        assert kwargs["fade_in"] == 1.0
        assert kwargs["fade_out"] == 2.0

    def test_with_overlays(self):
        recipe = Recipe(
            inputs=[RecipeInput(file="a.mp4")],
            overlays=[
                RecipeOverlay(type="title", text="My Title", duration=5.0),
                RecipeOverlay(type="watermark", text="(c) Test"),
            ],
        )
        kwargs = recipe_to_stitch_job(recipe)
        assert kwargs["title_text"] == "My Title"
        assert kwargs["title_duration"] == 5.0
        assert kwargs["watermark_text"] == "(c) Test"

    def test_with_trims(self):
        recipe = Recipe(
            inputs=[
                RecipeInput(file="a.mp4", trim={"start": 5.0, "end": 30.0}),
                RecipeInput(file="b.mp4", trim={"start": 0.0, "duration": 15.0}),
            ],
        )
        kwargs = recipe_to_stitch_job(recipe)
        assert len(kwargs["trims"]) == 2
        assert kwargs["trims"][0].start == 5.0
        assert kwargs["trims"][0].end == 30.0
        assert kwargs["trims"][1].duration == 15.0


class TestLoadRecipe:
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_recipe("nonexistent.json")

    def test_invalid_json(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{invalid json}")
        with pytest.raises(ValueError):
            load_recipe(str(bad))

    def test_valid_recipe(self, tmp_path):
        data = {
            "version": "1.0",
            "metadata": {"title": "Test"},
            "inputs": [
                {"file": "test.mp4", "label": "Clip 1"}
            ],
            "output": {"file": "out.mp4", "format": "mp4"},
        }
        recipe_file = tmp_path / "recipe.json"
        recipe_file.write_text(json.dumps(data))
        # File won't exist, but parsing should work
        try:
            load_recipe(str(recipe_file))
        except ValueError as e:
            # Expected: "file not found" for test.mp4
            assert "file not found" in str(e)
