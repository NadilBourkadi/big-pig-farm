"""Source code generator for indicator sprite pixel data."""

import sys

from tools.sprite_export import format_grid_python, pixels_from_json

# Everything above this marker in indicator_pixels.py is preserved on regeneration.
_SPLIT_MARKER = "# --- GENERATED BELOW"


def generate_indicator_pixels_source(
    normal_sprites: dict,
    close_sprites: dict,
    existing_source: str,
) -> str:
    """Generate indicator_pixels.py source, preserving palettes and header.

    Keeps everything up to and including the GENERATED BELOW marker line,
    then regenerates the pixel grid sections from the editor JSON data.
    """
    idx = existing_source.find(_SPLIT_MARKER)
    if idx < 0:
        print(f"Error: could not find '{_SPLIT_MARKER}' marker in indicator_pixels.py")
        sys.exit(1)

    # Find end of the marker line
    end = existing_source.index("\n", idx)
    header = existing_source[: end + 1]
    lines = [header.rstrip("\n"), ""]

    # Normal-zoom sprites
    lines.append("# " + "-" * 75)
    lines.append("# Normal zoom pixel grids")
    lines.append("# " + "-" * 75)
    lines.append("")
    lines.append("INDICATOR_PIXELS_NORMAL: dict[str, PixelGrid] = {")

    for name, data in normal_sprites.items():
        grid = pixels_from_json(data)
        lines.append(f'    "{name}": {format_grid_python(grid)},')

    lines.append("}")
    lines.append("")
    lines.append("")

    # Close-zoom sprites
    lines.append("# " + "-" * 75)
    lines.append("# Close zoom pixel grids (2× normal)")
    lines.append("# " + "-" * 75)
    lines.append("")
    lines.append("INDICATOR_PIXELS_CLOSE: dict[str, PixelGrid] = {")

    for name, data in close_sprites.items():
        grid = pixels_from_json(data)
        lines.append(f'    "{name}": {format_grid_python(grid)},')

    lines.append("}")
    lines.append("")
    lines.append("# fmt: on")
    lines.append("")

    return "\n".join(lines)
