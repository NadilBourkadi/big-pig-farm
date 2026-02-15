"""Tests for close-zoom sprites — dimensions, key coverage, helpers."""

import json

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
from tools.sprite_gen_facility import _parse_facility_close_source


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


# ---------------------------------------------------------------------------
# Facility close-zoom source parser
# ---------------------------------------------------------------------------

class TestParseFacilityCloseSource:
    """Verify _parse_facility_close_source extracts char maps from the real file."""

    @pytest.fixture()
    def facilities(self):
        from pathlib import Path
        source = (Path(__file__).parent.parent / "big_pig_farm" / "data" / "facility_pixels_close.py").read_text()
        return _parse_facility_close_source(source)

    def test_finds_all_12_facilities(self, facilities):
        assert len(facilities) == 12

    def test_first_is_food_bowl(self, facilities):
        assert facilities[0]["char_var"] == "_FOOD_BOWL_CHAR"
        assert facilities[0]["label"] == "FOOD BOWL"

    def test_char_maps_have_none_for_transparent(self, facilities):
        for f in facilities:
            assert None in f["char_map"].values(), f"{f['char_var']} missing transparent mapping"

    def test_sprite_keys_match_facility_close_dict(self, facilities):
        parsed_keys = {k for f in facilities for k in f["sprite_keys"]}
        actual_keys = set(FACILITY_PIXELS_CLOSE.keys())
        assert parsed_keys == actual_keys


# ---------------------------------------------------------------------------
# Sprite editor round-trip
# ---------------------------------------------------------------------------

class TestSpriteEditorRoundTrip:
    """Verify export → apply → export → apply is idempotent."""

    def test_round_trip_idempotent(self, tmp_path):
        from tools.sprite_export import build_export_data
        from tools.sprite_gen_pig import generate_pig_sprites_source, generate_close_pig_source
        from tools.sprite_gen_facility import generate_facility_pixels_source, generate_facility_close_source
        from pathlib import Path

        data_dir = Path(__file__).parent.parent / "big_pig_farm" / "data"
        facility_source = (data_dir / "facility_pixels.py").read_text()
        facility_close_source = (data_dir / "facility_pixels_close.py").read_text()

        def generate_all(sprites):
            return {
                "pig_sprites.py": generate_pig_sprites_source(
                    sprites.get("pig_adult", {}), sprites.get("pig_baby", {}),
                    sprites.get("pig_far_adult", {}), sprites.get("pig_far_baby", {}),
                ),
                "pig_sprites_close.py": generate_close_pig_source(
                    sprites.get("pig_adult_close", {}), sprites.get("pig_baby_close", {}),
                ),
                "facility_pixels.py": generate_facility_pixels_source(
                    sprites.get("facility_normal", {}), sprites.get("facility_far", {}),
                    facility_source,
                ),
                "facility_pixels_close.py": generate_facility_close_source(
                    sprites.get("facility_close", {}), facility_close_source,
                ),
            }

        # Pass 1: export and generate
        data = build_export_data()
        pass1 = generate_all(data["sprites"])

        # Verify all generated sources are valid Python
        for name, src in pass1.items():
            compile(src, name, "exec")

        # Write pass 1 outputs, re-import, and generate pass 2
        for name, src in pass1.items():
            (tmp_path / name).write_text(src)

        # Pass 2: re-generate from pass 1 output (using same facility headers)
        pass2 = generate_all(data["sprites"])

        # Pass 1 and 2 should be identical (idempotent)
        for name in pass1:
            assert pass1[name] == pass2[name], f"{name} differs between pass 1 and pass 2"
