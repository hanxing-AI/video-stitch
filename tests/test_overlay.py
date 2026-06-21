"""Tests for overlay.py."""

import pytest
from video_stitch.overlay import (
    TextOverlay, title_card, watermark,
    build_drawtext_filter, build_overlay_chain,
    _escape_drawtext,
)


class TestEscapeDrawtext:
    def test_simple(self):
        assert _escape_drawtext("hello") == "hello"

    def test_single_quote(self):
        result = _escape_drawtext("it's")
        assert "\\'" in result

    def test_colon(self):
        result = _escape_drawtext("a:b")
        assert "\\:" in result

    def test_backslash(self):
        result = _escape_drawtext("a\\b")
        assert "\\\\" in result


class TestTextOverlay:
    def test_defaults(self):
        ov = TextOverlay(text="Hello")
        assert ov.text == "Hello"
        assert ov.font_size == 48

    def test_validate_empty_text(self):
        ov = TextOverlay(text="")
        errors = ov.validate()
        assert len(errors) > 0

    def test_validate_ok(self):
        ov = TextOverlay(text="Hello")
        assert ov.validate() == []


class TestTitleCard:
    def test_creates_centered_overlay(self):
        tc = title_card("My Title", duration=5.0, font_size=72)
        assert tc.text == "My Title"
        assert tc.font_size == 72
        assert "between(t,0,5.000)" in tc.enable_expr
        assert "(main_w-text_w)/2" == tc.x_expr
        assert "(main_h-text_h)/2" == tc.y_expr

    def test_default_duration(self):
        tc = title_card("Title")
        assert "between(t,0,3.000)" in tc.enable_expr


class TestWatermark:
    def test_bottom_right(self):
        wm = watermark("(c) 2026", position="bottom-right")
        assert "main_w-text_w-20" in wm.x_expr
        assert "main_h-text_h-20" in wm.y_expr
        assert "between(t,0,999999)" in wm.enable_expr

    def test_bad_position(self):
        with pytest.raises(ValueError, match="Unknown position"):
            watermark("text", position="nowhere")


class TestBuildDrawtextFilter:
    def test_basic(self):
        ov = TextOverlay(text="Hello World")
        result = build_drawtext_filter(ov)
        assert "drawtext" in result
        assert "Hello World" in result
        assert "fontsize=48" in result

    def test_escapes_special_chars(self):
        ov = TextOverlay(text="It's a: test")
        result = build_drawtext_filter(ov)
        assert "\\'" in result
        assert "\\:" in result

    def test_with_font_file(self):
        ov = TextOverlay(text="Hello", font_file="/fonts/arial.ttf")
        result = build_drawtext_filter(ov)
        assert "fontfile=" in result


class TestBuildOverlayChain:
    def test_empty_overlays(self):
        result = build_overlay_chain([])
        assert result == ""

    def test_single_overlay(self):
        ov = TextOverlay(text="Title")
        result = build_overlay_chain([ov])
        assert "drawtext" in result
        assert "[base]" in result
        assert "[v]" in result

    def test_multiple_overlays(self):
        ov1 = TextOverlay(text="Title", enable_expr="between(t,0,3)")
        ov2 = TextOverlay(text="WM", enable_expr="between(t,0,999)")
        result = build_overlay_chain([ov1, ov2])
        assert ";" in result
        assert "[ov0]" in result
        assert "[v]" in result
