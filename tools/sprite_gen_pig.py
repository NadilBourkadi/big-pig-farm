"""Source code generators for pig sprite Python files."""

import json

from tools.sprite_export import (
    encode_sprite_line,
    format_grid_python,
    mirror_grid,
    pixels_from_json,
)


def _make_var_name(key: str, prefix: str) -> str:
    """Generate a Python variable name, e.g. 'idle_right' -> '_CLOSE_IDLE_R'."""
    suffix = key.replace("_right", "_r").replace("_left", "_l").upper()
    return f"{prefix}{suffix}"


def _detect_aliases(
    sprite_data: dict,
) -> tuple[dict[str, list[list]], dict[str, str]]:
    """Detect which sprites share identical pixel data.

    Returns:
        unique: dict mapping sprite key -> pixel grid (first occurrence wins)
        alias_to_source: dict mapping alias key -> source key it duplicates
    """
    unique: dict[str, list[list]] = {}
    alias_to_source: dict[str, str] = {}
    seen: dict[str, str] = {}
    for key in sprite_data:
        grid = pixels_from_json(sprite_data[key])
        grid_str = json.dumps(grid)
        if grid_str in seen:
            alias_to_source[key] = seen[grid_str]
        else:
            seen[grid_str] = key
            unique[key] = grid
    return unique, alias_to_source


def generate_pig_sprites_source(
    adult_sprites: dict, baby_sprites: dict,
    far_adult_sprites: dict, far_baby_sprites: dict,
) -> str:
    """Generate the full pig_sprites.py source from sprite data."""
    lines = [
        '"""Pig pixel sprite data — all zoom levels and animation frames.',
        "",
        "Normal-zoom adults are 14w x 8h pixels (14 x 4 half-block chars).",
        "Normal-zoom babies are 8w x 6h pixels.",
        "Far-zoom adults are 7w x 6h pixels, far-zoom babies are 5w x 4h pixels.",
        '"""',
        "",
        "from big_pig_farm.data.sprite_engine import T",
        "",
        "# Palette keys used:  fur, dark, belly, eye, nose, ear, paw, T(ransparent)",
        "",
        "# fmt: off",
        "",
        "# --- Adult sprites (14w x 8h pixels) ---",
        "",
        "PIG_PIXELS_ADULT = {",
    ]

    def add_sprite_dict(sprites: dict, lines_list: list) -> None:
        for key, data in sprites.items():
            grid = pixels_from_json(data)
            lines_list.append(f'    "{key}": {format_grid_python(grid)},')
            left_key = key.replace("_right", "_left")
            if left_key != key:
                left_grid = mirror_grid(grid)
                lines_list.append(
                    f'    "{left_key}": {format_grid_python(left_grid)},'
                )

    add_sprite_dict(adult_sprites, lines)
    lines.append("}")
    lines.append("")
    lines.append("# --- Baby sprites (8w x 6h pixels) ---")
    lines.append("")
    lines.append("PIG_PIXELS_BABY = {")
    add_sprite_dict(baby_sprites, lines)
    lines.append("}")
    lines.append("")
    lines.append(
        "# --- Far-zoom adult sprites (7w x 6h pixels -> 7x3 half-block chars) ---"
    )
    lines.append("")
    lines.append("PIG_PIXELS_FAR_ADULT = {")
    add_sprite_dict(far_adult_sprites, lines)
    lines.append("}")
    lines.append("")
    lines.append(
        "# --- Far-zoom baby sprites (5w x 4h pixels -> 5x2 half-block chars) ---"
    )
    lines.append("")
    lines.append("PIG_PIXELS_FAR_BABY = {")
    add_sprite_dict(far_baby_sprites, lines)
    lines.append("}")
    lines.append("")
    lines.append("# fmt: on")
    lines.append("")

    return "\n".join(lines)


def _generate_close_section(
    sprites: dict, var_prefix: str, dict_name: str,
    pig_char_map: dict[str, str],
) -> list[str]:
    """Generate close-zoom sprite variables and dict for one age group."""
    lines: list[str] = []
    unique, aliases = _detect_aliases(sprites)

    var_names: dict[str, str] = {}
    for key in unique:
        var_names[key] = _make_var_name(key, var_prefix)

    for key, var_name in var_names.items():
        data = sprites[key]
        grid = pixels_from_json(data)
        width = data["width"]
        encoded = [encode_sprite_line(row, pig_char_map) for row in grid]

        lines.append(f"{var_name}: PixelGrid = decode_sprite([")
        for eline in encoded:
            lines.append(f'    "{eline}",')
        lines.append(f"], _PIG_CHAR, width={width})")
        lines.append("")

    lines.append("")
    lines.append(
        "# Build combined dict — right-facing raw grids mapped to all states"
    )
    lines.append(f"{dict_name}: dict[str, PixelGrid] = build_mirrored_dict({{")
    for key in sprites:
        if key in var_names:
            var_ref = var_names[key]
            comment = ""
        else:
            source_key = aliases[key]
            var_ref = var_names[source_key]
            comment = f"  # same as {source_key}"
        padding = " " * max(0, 24 - len(f'"{key}"'))
        lines.append(f'    "{key}":{padding}{var_ref},{comment}')
    lines.append("})")
    lines.append("")

    return lines


def generate_close_pig_source(
    adult_sprites: dict, baby_sprites: dict,
) -> str:
    """Generate pig_sprites_close.py source."""
    pig_char_map = {
        "dark": "d", "fur": "f", "shade": "s", "belly": "b",
        "eye": "e", "pupil": "p", "nose": "n", "ear": "a", "paw": "w",
    }

    lines = [
        '"""Hand-crafted close-zoom pig pixel sprites (28w\u00d716h adult, 16w\u00d712h baby).',
        "",
        "Only right-facing variants are drawn here; left-facing ones are auto-generated",
        "by mirroring each row.  Uses compact single-char encoding decoded at import time.",
        "",
        "The silhouette (transparent vs non-transparent boundary) matches the 2x-scaled",
        "normal sprites exactly \u2014 this guarantees smooth outlines.  Interior pixels are",
        "refined to break up the 2x2 blockiness: ears, eyes, nose, and belly transitions",
        "differ between paired rows.",
        '"""',
        "",
        "from big_pig_farm.data.sprite_engine import (",
        "    PixelGrid,",
        "    build_mirrored_dict,",
        "    decode_sprite,",
        ")",
        "",
        "# Character maps \u2014 one char per palette key",
        "_PIG_CHAR = {",
        '    ".": None, "d": "dark", "f": "fur", "s": "shade", "b": "belly",',
        '    "e": "eye", "p": "pupil", "n": "nose", "a": "ear", "w": "paw",',
        "}",
        "",
        "# fmt: off",
        "",
        "# ---------------------------------------------------------------------------",
        "# Adult close-zoom sprites (28w \u00d7 16h)",
        "#",
        "# Silhouette matches scale_pixel_grid(normal, 2) exactly.",
        "# Interior detail refined: each row pair is unpaired for less blockiness.",
        "# ---------------------------------------------------------------------------",
        "",
    ]

    lines.extend(
        _generate_close_section(
            adult_sprites, "_CLOSE_", "PIG_PIXELS_CLOSE_ADULT", pig_char_map
        )
    )

    lines.extend([
        "",
        "# ---------------------------------------------------------------------------",
        "# Baby close-zoom sprites (16w \u00d7 12h)",
        "#",
        "# Same approach: silhouette matches 2x-scaled, interior refined.",
        "# ---------------------------------------------------------------------------",
        "",
    ])

    lines.extend(
        _generate_close_section(
            baby_sprites, "_BABY_", "PIG_PIXELS_CLOSE_BABY", pig_char_map
        )
    )

    lines.append("# fmt: on")
    lines.append("")

    return "\n".join(lines)
