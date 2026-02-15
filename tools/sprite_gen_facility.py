"""Source code generators for facility sprite Python files."""

import ast
import re
import sys

from tools.sprite_export import (
    encode_sprite_line,
    format_grid_python,
    pixels_from_json,
)


# ---------------------------------------------------------------------------
# Parse char maps from existing source (avoids hardcoding)
# ---------------------------------------------------------------------------

def _parse_facility_close_source(source: str) -> list[dict]:
    """Parse facility_pixels_close.py to extract char maps and sprite associations.

    Returns a list of facility entries in source order, each with:
        char_var: variable name (e.g. "_FOOD_BOWL_CHAR")
        char_map: decode dict (char -> palette_key or None)
        label:    display label (e.g. "FOOD BOWL")
        sprite_keys: ordered list of sprite keys using this char map
    """
    # Extract char map definitions
    char_map_re = re.compile(
        r'^(_\w+_CHAR)\s*=\s*\{([^}]*)\}', re.MULTILINE,
    )
    char_maps: dict[str, dict] = {}
    char_var_order: list[str] = []
    for m in char_map_re.finditer(source):
        var_name = m.group(1)
        char_maps[var_name] = ast.literal_eval("{" + m.group(2) + "}")
        char_var_order.append(var_name)

    # Extract sprite -> char_var associations
    sprite_re = re.compile(
        r'FACILITY_PIXELS_CLOSE\["(\w+)"\]\s*=\s*decode_sprite\(\[.*?\],\s*'
        r'(_\w+_CHAR),\s*width=(\d+)\)',
        re.DOTALL,
    )
    facilities: dict[str, list[str]] = {}
    for m in sprite_re.finditer(source):
        key, char_var = m.group(1), m.group(2)
        facilities.setdefault(char_var, []).append(key)

    # Build result in source order
    result = []
    for char_var in char_var_order:
        if char_var not in facilities:
            continue
        sprite_keys = facilities[char_var]
        base_type = re.sub(r'_(empty|full)$', '', sprite_keys[0])
        result.append({
            "char_var": char_var,
            "char_map": char_maps[char_var],
            "label": base_type.upper().replace("_", " "),
            "sprite_keys": sprite_keys,
        })
    return result


# ---------------------------------------------------------------------------
# Normal + far zoom generator
# ---------------------------------------------------------------------------

def generate_facility_pixels_source(
    normal_sprites: dict, far_sprites: dict,
    existing_source: str,
) -> str:
    """Generate facility_pixels.py source, preserving FACILITY_PALETTES header."""
    marker = "\n# fmt: off\n"
    idx = existing_source.find(marker)
    if idx < 0:
        print("Error: could not find '# fmt: off' marker in facility_pixels.py")
        sys.exit(1)

    header = existing_source[: idx + len(marker)]
    lines = [header.rstrip("\n"), ""]

    # Derive facility order dynamically from sprite keys
    facility_types: dict[str, str] = {}
    for key in normal_sprites:
        base = re.sub(r'_(empty|full)$', '', key)
        if base not in facility_types:
            facility_types[base] = base.upper().replace("_", " ")

    # Normal-zoom sprites
    lines.append("FACILITY_PIXELS: dict[str, PixelGrid] = {")

    for base_type, label in facility_types.items():
        keys = [k for k in normal_sprites if k == base_type or k.startswith(base_type + "_")]
        if not keys:
            continue

        first = normal_sprites[keys[0]]
        w, h = first["width"], first["height"]
        hb_h = (h + 1) // 2

        lines.append(f"    # {'-' * 71}")
        lines.append(f"    # {label}  ({w}w x {h}h -> {w}x{hb_h})")
        lines.append(f"    # {'-' * 71}")

        for key in keys:
            grid = pixels_from_json(normal_sprites[key])
            lines.append(f'    "{key}": {format_grid_python(grid)},')
        lines.append("")

    lines.append("}")
    lines.append("")
    lines.append("")

    # Far-zoom sprites
    lines.append("# " + "-" * 75)
    lines.append("# Far-zoom pixel grids (compact icons for zoomed-out view)")
    lines.append("# " + "-" * 75)
    lines.append("")
    lines.append("FACILITY_PIXELS_FAR: dict[str, PixelGrid] = {")

    for base_type, label in facility_types.items():
        if base_type not in far_sprites:
            continue
        data = far_sprites[base_type]
        grid = pixels_from_json(data)
        w, h = data["width"], data["height"]
        hb_h = (h + 1) // 2

        lines.append(f"    # {label} ({w}w x {h}h -> {w}x{hb_h})")
        lines.append(f'    "{base_type}": {format_grid_python(grid)},')

    lines.append("}")
    lines.append("")
    lines.append("# fmt: on")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Close-zoom generator
# ---------------------------------------------------------------------------

def generate_facility_close_source(
    close_sprites: dict,
    existing_source: str,
) -> str:
    """Generate facility_pixels_close.py source, parsing char maps from existing file."""
    facilities = _parse_facility_close_source(existing_source)

    # Warn about sprites not covered by parsed facilities
    known_keys = {k for f in facilities for k in f["sprite_keys"]}
    for key in close_sprites:
        if key not in known_keys:
            print(f"Warning: unknown facility sprite '{key}' will be skipped in close-zoom output")

    lines = [
        '"""Hand-crafted close-zoom facility pixel sprites (2x normal dimensions).',
        "",
        "Uses compact single-char encoding decoded at import time.",
        "Each facility has its own char map matching its palette keys.",
        '"""',
        "",
        "from big_pig_farm.data.sprite_engine import PixelGrid, decode_sprite",
        "",
        "# fmt: off",
        "",
    ]

    for i, facility in enumerate(facilities):
        char_var = facility["char_var"]
        char_map = facility["char_map"]
        label = facility["label"]
        sprite_keys = facility["sprite_keys"]

        data0 = close_sprites.get(sprite_keys[0])
        w, h = (data0["width"], data0["height"]) if data0 else ("?", "?")

        lines.append(f"# {'-' * 75}")
        lines.append(f"# {label} ({w}w \u00d7 {h}h)")
        lines.append(f"# {'-' * 75}")
        lines.append("")

        # Format char map (decode direction: char -> palette_key)
        char_items = []
        for ch, pk in char_map.items():
            if pk is None:
                char_items.append('".": None')
            else:
                char_items.append(f'"{ch}": "{pk}"')
        lines.append(f"{char_var} = {{")
        lines.append(f"    {', '.join(char_items)},")
        lines.append("}")
        lines.append("")

        if i == 0:
            lines.append("FACILITY_PIXELS_CLOSE: dict[str, PixelGrid] = {}")
            lines.append("")

        # Build reverse map for encoding: palette_key -> char
        key_to_char = {pk: ch for ch, pk in char_map.items() if pk is not None}

        for sprite_key in sprite_keys:
            if sprite_key not in close_sprites:
                continue
            data = close_sprites[sprite_key]
            grid = pixels_from_json(data)
            width = data["width"]
            encoded = [encode_sprite_line(row, key_to_char) for row in grid]

            lines.append(f'FACILITY_PIXELS_CLOSE["{sprite_key}"] = decode_sprite([')
            for eline in encoded:
                lines.append(f'    "{eline}",')
            lines.append(f"], {char_var}, width={width})")
            lines.append("")

    lines.append("# fmt: on")
    lines.append("")

    return "\n".join(lines)
