"""Sprite data export — reads game sprites, resolves colors, builds JSON."""

from rich.color import Color

from big_pig_farm.data.sprite_engine import PALETTES
from big_pig_farm.data.pig_sprites import (
    PIG_PIXELS_ADULT,
    PIG_PIXELS_BABY,
    PIG_PIXELS_FAR_ADULT,
    PIG_PIXELS_FAR_BABY,
)
from big_pig_farm.data.pig_sprites_close import (
    PIG_PIXELS_CLOSE_ADULT,
    PIG_PIXELS_CLOSE_BABY,
)
from big_pig_farm.data.facility_pixels import (
    FACILITY_PALETTES,
    FACILITY_PIXELS,
    FACILITY_PIXELS_FAR,
)
from big_pig_farm.data.facility_pixels_close import FACILITY_PIXELS_CLOSE
from big_pig_farm.data.indicator_pixels import (
    INDICATOR_PALETTES,
    INDICATOR_PIXELS_CLOSE,
    INDICATOR_PIXELS_NORMAL,
)


# ---------------------------------------------------------------------------
# Color resolution
# ---------------------------------------------------------------------------

def resolve_color_to_hex(color_name: str) -> str:
    """Resolve a Rich color name to a hex RGB string."""
    try:
        c = Color.parse(color_name)
        rgb = c.get_truecolor()
        return f"#{rgb.red:02x}{rgb.green:02x}{rgb.blue:02x}"
    except Exception:
        if color_name.startswith("#"):
            return color_name
        return "#ff00ff"  # magenta fallback


def resolve_palette(palette: dict) -> dict[str, str]:
    """Resolve all color values in a palette to hex."""
    resolved = {}
    for key, value in palette.items():
        if key is None:
            resolved["T"] = resolve_color_to_hex(value)
        else:
            resolved[key] = resolve_color_to_hex(value)
    return resolved


# ---------------------------------------------------------------------------
# Grid serialisation / shared helpers
# ---------------------------------------------------------------------------

def grid_to_json(grid: list[list]) -> dict:
    """Convert a PixelGrid to a JSON-serialisable dict with dimensions."""
    height = len(grid)
    width = max((len(row) for row in grid), default=0)
    pixels = []
    for row in grid:
        json_row = [row[x] if x < len(row) else None for x in range(width)]
        pixels.append(json_row)
    return {"width": width, "height": height, "pixels": pixels}


def collect_right_facing(sprites: dict) -> dict:
    """Filter to only right-facing and non-directional sprite keys."""
    return {
        key: grid_to_json(grid)
        for key, grid in sprites.items()
        if "_left" not in key
    }


def collect_all(sprites: dict) -> dict:
    """Collect all sprite keys (for sprites without left/right distinction)."""
    return {key: grid_to_json(grid) for key, grid in sprites.items()}


def pixels_from_json(sprite_data: dict) -> list[list]:
    """Convert JSON sprite data back to a PixelGrid."""
    return sprite_data["pixels"]


def format_pixel(px) -> str:
    """Format a single pixel value as Python source."""
    if px is None:
        return " T  "
    return repr(px)


def format_grid_python(grid: list[list], indent: str = "        ") -> str:
    """Format a PixelGrid as Python source code (explicit list-of-lists)."""
    lines = ["["]
    for row in grid:
        cells = ", ".join(format_pixel(px) for px in row)
        lines.append(f"{indent}[{cells}],")
    lines.append(f"{indent[:-4]}]")
    return "\n".join(lines)


def mirror_grid(grid: list[list]) -> list[list]:
    """Mirror a pixel grid horizontally."""
    return [list(reversed(row)) for row in grid]


def encode_sprite_line(row: list, key_to_char: dict[str, str]) -> str:
    """Encode a pixel row as a compact single-char string, stripping trailing dots."""
    result = []
    for px in row:
        if px is None:
            result.append(".")
        else:
            result.append(key_to_char.get(px, "?"))
    return "".join(result).rstrip(".")


# ---------------------------------------------------------------------------
# Export data builder
# ---------------------------------------------------------------------------

def build_export_data() -> dict:
    """Build the complete JSON data structure for the editor."""
    pig_palettes = {name: resolve_palette(pal) for name, pal in PALETTES.items()}
    fac_palettes = {name: resolve_palette(pal) for name, pal in FACILITY_PALETTES.items()}
    ind_palettes = {
        name: resolve_palette(variants["bright"])
        for name, variants in INDICATOR_PALETTES.items()
    }

    pig_keys = [k for k in PALETTES["BLACK"] if k is not None]
    fac_palette_keys = {
        name: [k for k in pal if k is not None]
        for name, pal in FACILITY_PALETTES.items()
    }
    ind_palette_keys = {
        name: list(variants["bright"].keys())
        for name, variants in INDICATOR_PALETTES.items()
    }

    sprites = {
        "pig_adult": collect_right_facing(PIG_PIXELS_ADULT),
        "pig_baby": collect_right_facing(PIG_PIXELS_BABY),
        "pig_far_adult": collect_right_facing(PIG_PIXELS_FAR_ADULT),
        "pig_far_baby": collect_right_facing(PIG_PIXELS_FAR_BABY),
        "pig_adult_close": collect_right_facing(PIG_PIXELS_CLOSE_ADULT),
        "pig_baby_close": collect_right_facing(PIG_PIXELS_CLOSE_BABY),
        "facility_normal": collect_all(FACILITY_PIXELS),
        "facility_far": collect_all(FACILITY_PIXELS_FAR),
        "facility_close": collect_all(FACILITY_PIXELS_CLOSE),
        "indicator_normal": collect_all(INDICATOR_PIXELS_NORMAL),
        "indicator_close": collect_all(INDICATOR_PIXELS_CLOSE),
    }

    return {
        "format_version": 1,
        "palettes": {"pig": pig_palettes, "facility": fac_palettes, "indicator": ind_palettes},
        "palette_keys": {"pig": pig_keys, "facility": fac_palette_keys, "indicator": ind_palette_keys},
        "sprites": sprites,
    }
