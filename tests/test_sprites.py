"""Tests for close-zoom sprites — dimensions, key coverage, helpers."""

import pytest

from big_pig_farm.data.sprite_engine import (
    decode_sprite,
    mirror_grid,
    build_mirrored_dict,
    scale_pixel_grid,
)
from big_pig_farm.data.pig_sprites import PIG_PIXELS_ADULT, PIG_PIXELS_BABY
from big_pig_farm.data.pig_sprites_close import (
    PIG_PIXELS_CLOSE_ADULT,
    PIG_PIXELS_CLOSE_BABY,
)
from big_pig_farm.data.facility_pixels import FACILITY_PIXELS
from big_pig_farm.data.facility_pixels_close import FACILITY_PIXELS_CLOSE
from big_pig_farm.data.pig_sprite_lookup import get_pig_pixel_sprite


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestDecodeSprite:
    def test_basic_decode(self):
        char_map = {".": None, "f": "fur", "d": "dark"}
        grid = decode_sprite(["f.d", "dff"], char_map)
        assert grid == [["fur", None, "dark"], ["dark", "fur", "fur"]]

    def test_width_padding(self):
        char_map = {".": None, "f": "fur"}
        grid = decode_sprite(["ff", "f"], char_map, width=4)
        assert len(grid[0]) == 4
        assert len(grid[1]) == 4
        assert grid[1] == ["fur", None, None, None]

    def test_unknown_char_maps_to_none(self):
        char_map = {".": None, "f": "fur"}
        grid = decode_sprite(["fxf"], char_map)
        assert grid[0] == ["fur", None, "fur"]


class TestMirrorGrid:
    def test_mirror_reverses_rows(self):
        grid = [["a", "b", "c"], ["d", "e", "f"]]
        mirrored = mirror_grid(grid)
        assert mirrored == [["c", "b", "a"], ["f", "e", "d"]]

    def test_mirror_preserves_height(self):
        grid = [[None, "fur"], ["dark", None], [None, None]]
        mirrored = mirror_grid(grid)
        assert len(mirrored) == 3

    def test_double_mirror_is_identity(self):
        grid = [["a", None, "b"], [None, "c", None]]
        assert mirror_grid(mirror_grid(grid)) == grid


class TestBuildMirroredDict:
    def test_creates_left_variants(self):
        right_grid = [["a", "b"]]
        result = build_mirrored_dict({"idle_right": right_grid})
        assert "idle_right" in result
        assert "idle_left" in result
        assert result["idle_left"] == [["b", "a"]]

    def test_preserves_right_grid(self):
        right_grid = [["a", "b", "c"]]
        result = build_mirrored_dict({"idle_right": right_grid})
        assert result["idle_right"] is right_grid


# ---------------------------------------------------------------------------
# Adult close-zoom pig sprite dimensions (28w × 16h)
# ---------------------------------------------------------------------------

class TestAdultCloseSpriteDimensions:
    @pytest.mark.parametrize("key", list(PIG_PIXELS_CLOSE_ADULT.keys()))
    def test_height_is_16(self, key):
        grid = PIG_PIXELS_CLOSE_ADULT[key]
        assert len(grid) == 16, f"{key} height {len(grid)} != 16"

    @pytest.mark.parametrize("key", list(PIG_PIXELS_CLOSE_ADULT.keys()))
    def test_width_is_28(self, key):
        grid = PIG_PIXELS_CLOSE_ADULT[key]
        widths = {len(row) for row in grid}
        assert widths == {28}, f"{key} widths {widths} != {{28}}"


# ---------------------------------------------------------------------------
# Baby close-zoom pig sprite dimensions (16w × 12h)
# ---------------------------------------------------------------------------

class TestBabyCloseSpriteDimensions:
    @pytest.mark.parametrize("key", list(PIG_PIXELS_CLOSE_BABY.keys()))
    def test_height_is_12(self, key):
        grid = PIG_PIXELS_CLOSE_BABY[key]
        assert len(grid) == 12, f"{key} height {len(grid)} != 12"

    @pytest.mark.parametrize("key", list(PIG_PIXELS_CLOSE_BABY.keys()))
    def test_width_is_16(self, key):
        grid = PIG_PIXELS_CLOSE_BABY[key]
        widths = {len(row) for row in grid}
        assert widths == {16}, f"{key} widths {widths} != {{16}}"


# ---------------------------------------------------------------------------
# Key coverage — every normal-zoom key has a close-zoom counterpart
# ---------------------------------------------------------------------------

class TestKeyCoverage:
    def test_adult_close_covers_normal_keys(self):
        for key in PIG_PIXELS_ADULT:
            assert key in PIG_PIXELS_CLOSE_ADULT, f"Missing adult close key: {key}"

    def test_baby_close_covers_normal_keys(self):
        for key in PIG_PIXELS_BABY:
            assert key in PIG_PIXELS_CLOSE_BABY, f"Missing baby close key: {key}"

    def test_facility_close_covers_normal_keys(self):
        for key in FACILITY_PIXELS:
            assert key in FACILITY_PIXELS_CLOSE, f"Missing facility close key: {key}"


# ---------------------------------------------------------------------------
# Facility close-zoom dimensions (2x normal)
# ---------------------------------------------------------------------------

class TestFacilityCloseSpriteDimensions:
    @pytest.mark.parametrize("key", list(FACILITY_PIXELS_CLOSE.keys()))
    def test_dimensions_are_2x_normal(self, key):
        # Get base key (strip state suffix for normal lookup)
        close_grid = FACILITY_PIXELS_CLOSE[key]
        normal_grid = FACILITY_PIXELS.get(key)
        if normal_grid is None:
            pytest.skip(f"No normal-zoom grid for {key}")
        normal_h = len(normal_grid)
        normal_w = max(len(r) for r in normal_grid)
        close_h = len(close_grid)
        close_w = max(len(r) for r in close_grid)
        assert close_w == normal_w * 2, f"{key} width {close_w} != {normal_w * 2}"
        assert close_h == normal_h * 2, f"{key} height {close_h} != {normal_h * 2}"


# ---------------------------------------------------------------------------
# Lookup fallback
# ---------------------------------------------------------------------------

class TestPigSpriteFallback:
    def test_close_zoom_returns_28x16_for_adult(self):
        grid = get_pig_pixel_sprite("idle", "right", is_baby=False, close_zoom=True)
        assert len(grid) == 16
        assert all(len(row) == 28 for row in grid)

    def test_close_zoom_returns_16x12_for_baby(self):
        grid = get_pig_pixel_sprite("idle", "right", is_baby=True, close_zoom=True)
        assert len(grid) == 12
        assert all(len(row) == 16 for row in grid)

    def test_unknown_state_falls_back_to_idle(self):
        grid = get_pig_pixel_sprite("nonexistent", "right", close_zoom=True)
        idle_grid = get_pig_pixel_sprite("idle", "right", close_zoom=True)
        assert grid == idle_grid

    def test_normal_zoom_unchanged(self):
        grid = get_pig_pixel_sprite("idle", "right", close_zoom=False)
        assert len(grid) == 8  # normal adult is 8h
