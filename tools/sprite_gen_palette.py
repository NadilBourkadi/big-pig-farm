"""Palette write-back — update Python source files with edited palette colours.

Each writer takes palette data from the editor (hex colours) and regenerates
the corresponding Python dict in the target source file using regex replacement.
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "big_pig_farm" / "data"
SPRITE_ENGINE_FILE = DATA_DIR / "sprite_engine.py"
FACILITY_PIXELS_FILE = DATA_DIR / "facility_pixels.py"
INDICATOR_PIXELS_FILE = DATA_DIR / "indicator_pixels.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hex_upper(hex_color: str) -> str:
    """Normalise a hex colour to uppercase #RRGGBB."""
    return hex_color.upper() if hex_color.startswith("#") else hex_color


def _darken_hex(hex_color: str, factor: float = 0.65) -> str:
    """Darken a hex colour by a factor (0.65 = 35% darker)."""
    hex_color = hex_color.lstrip("#")
    r = int(int(hex_color[0:2], 16) * factor)
    g = int(int(hex_color[2:4], 16) * factor)
    b = int(int(hex_color[4:6], 16) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def _max_key_len(keys: list[str]) -> int:
    """Longest key length for alignment padding."""
    return max((len(k) for k in keys), default=1)


# ---------------------------------------------------------------------------
# Pig palettes — sprite_engine.py
# ---------------------------------------------------------------------------

def _generate_pig_palettes_source(
    pig_palettes: dict[str, dict[str, str]],
    palette_keys: list[str],
) -> str:
    """Generate the PALETTES dict source code.

    The T key (Python None) is set to match the "fur" value for each variant.
    """
    lines = ['PALETTES: dict[str, dict[str, str]] = {']
    # Determine alignment width: longest among palette_keys + "T" label
    pad = _max_key_len(palette_keys)

    for variant_name, colours in pig_palettes.items():
        lines.append(f'    "{variant_name}": {{')
        for key in palette_keys:
            hex_val = colours.get(key, "#ff00ff")
            lines.append(f'        "{key}":{" " * (pad - len(key))} "{hex_val}",')
        # T key: same as fur
        fur_val = colours.get("fur", "#ff00ff")
        lines.append(f'         T:{" " * (pad - 1)} "{fur_val}",')
        lines.append('    },')

    lines.append('}')
    return "\n".join(lines)


def apply_pig_palettes(
    pig_palettes: dict[str, dict[str, str]],
    palette_keys: list[str],
    source: str | None = None,
) -> str:
    """Rewrite PALETTES dict in sprite_engine.py. Returns the updated source.

    If *source* is provided, it is used instead of reading from disk (allows
    chaining with other writers that modify the same file).
    """
    if source is None:
        source = SPRITE_ENGINE_FILE.read_text(encoding="utf-8")
    new_dict = _generate_pig_palettes_source(pig_palettes, palette_keys)

    pattern = r"^PALETTES: dict\[str, dict\[str, str\]\] = \{.*?^\}"
    updated = re.sub(pattern, new_dict, source, count=1, flags=re.MULTILINE | re.DOTALL)

    if updated == source:
        raise ValueError("Could not find PALETTES dict to replace in sprite_engine.py")
    return updated


# ---------------------------------------------------------------------------
# Facility palettes — facility_pixels.py
# ---------------------------------------------------------------------------

def _generate_facility_palettes_source(
    facility_palettes: dict[str, dict[str, str]],
) -> str:
    """Generate the FACILITY_PALETTES dict source code."""
    lines = ['FACILITY_PALETTES: dict[str, dict[str, str]] = {']

    for ftype, colours in facility_palettes.items():
        lines.append(f'    "{ftype}": {{')
        pad = _max_key_len(list(colours.keys()))
        for key, hex_val in colours.items():
            lines.append(f'        "{key}":{" " * (pad - len(key))} "{_hex_upper(hex_val)}",')
        lines.append('    },')

    lines.append('}')
    return "\n".join(lines)


def apply_facility_palettes(
    facility_palettes: dict[str, dict[str, str]],
    source: str | None = None,
) -> str:
    """Rewrite FACILITY_PALETTES dict in facility_pixels.py. Returns updated source."""
    if source is None:
        source = FACILITY_PIXELS_FILE.read_text(encoding="utf-8")
    new_dict = _generate_facility_palettes_source(facility_palettes)

    pattern = r"^FACILITY_PALETTES: dict\[str, dict\[str, str\]\] = \{.*?^\}"
    updated = re.sub(pattern, new_dict, source, count=1, flags=re.MULTILINE | re.DOTALL)

    if updated == source:
        raise ValueError("Could not find FACILITY_PALETTES dict to replace in facility_pixels.py")
    return updated


# ---------------------------------------------------------------------------
# Indicator palettes — indicator_pixels.py
# ---------------------------------------------------------------------------

def _generate_indicator_palettes_source(
    indicator_palettes: dict[str, dict[str, str]],
) -> str:
    """Generate the INDICATOR_PALETTES dict source code.

    The editor only provides the 'bright' variant; the 'dim' variant is
    auto-computed by darkening each colour ~35%.
    """
    lines = ['INDICATOR_PALETTES: dict[str, dict[str, dict[str, str]]] = {']

    for ind_name, bright_colours in indicator_palettes.items():
        bright_inner = ", ".join(
            f'"{k}": "{v}"' for k, v in bright_colours.items()
        )
        dim_colours = {k: _darken_hex(v) for k, v in bright_colours.items()}
        dim_inner = ", ".join(
            f'"{k}": "{v}"' for k, v in dim_colours.items()
        )
        lines.append(f'    "{ind_name}": {{')
        lines.append(f'        "bright": {{{bright_inner}}},')
        lines.append(f'        "dim":    {{{dim_inner}}},')
        lines.append('    },')

    lines.append('}')
    return "\n".join(lines)


def apply_indicator_palettes(
    indicator_palettes: dict[str, dict[str, str]],
    source: str | None = None,
) -> str:
    """Rewrite INDICATOR_PALETTES dict in indicator_pixels.py. Returns updated source."""
    if source is None:
        source = INDICATOR_PIXELS_FILE.read_text(encoding="utf-8")
    new_dict = _generate_indicator_palettes_source(indicator_palettes)

    pattern = r"^INDICATOR_PALETTES: dict\[str, dict\[str, dict\[str, str\]\]\] = \{.*?^\}"
    updated = re.sub(pattern, new_dict, source, count=1, flags=re.MULTILINE | re.DOTALL)

    if updated == source:
        raise ValueError("Could not find INDICATOR_PALETTES dict to replace in indicator_pixels.py")
    return updated
