"""Half-block pixel rendering engine — types, palettes, and conversion functions.

Unicode half-block characters (▀▄█ ) give 2 vertical pixels per terminal cell.
All sprites — farm, portraits, UI — share the convert_pixels() pipeline.
"""

from typing import Optional

from rich.text import Text
from rich.style import Style


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------

# Type aliases for clarity
PixelGrid = list[list[Optional[str]]]  # 2D grid of palette keys or None (transparent)
HalfBlockRow = list[tuple[str, Optional[str], Optional[str]]]  # (char, fg, bg)
HalfBlockRows = list[HalfBlockRow]

# Transparent sentinel
T = None

# Animation timing: ticks per frame for each animated display state.
# States not listed here are static (single frame).
ANIM_TICKS_PER_FRAME: dict[str, int] = {
    "walking": 3,
    "eating": 4,
    "happy": 3,
    "sleeping": 10,
}

# Number of animation frames per state.  States not listed default to 2.
ANIM_FRAME_COUNT: dict[str, int] = {
    "walking": 3,
    "eating": 2,
    "happy": 2,
    "sleeping": 2,
}


# ---------------------------------------------------------------------------
# Core converter
# ---------------------------------------------------------------------------

def convert_pixels(
    grid: PixelGrid,
    palette: Optional[dict[str, str]] = None,
) -> HalfBlockRows:
    """Convert a pixel grid to half-block character rows.

    Args:
        grid: 2D array of color keys (or raw Rich color strings). None = transparent.
        palette: Optional mapping from color key -> Rich color string.
                 If provided, every non-None pixel is looked up. If None,
                 pixel values are used as literal color strings.

    Returns:
        List of rows, each row a list of (char, fg_color, bg_color) tuples.
        fg/bg may be None when the cell is fully transparent.
    """
    # Pad grid to even row count
    height = len(grid)
    width = max((len(row) for row in grid), default=0)
    if height % 2 != 0:
        grid = list(grid) + [[T] * width]
        height += 1

    def resolve(px: Optional[str]) -> Optional[str]:
        if px is None:
            return None
        if palette and px in palette:
            return palette[px]
        return px

    rows: HalfBlockRows = []
    for y in range(0, height, 2):
        row_top = grid[y] if y < len(grid) else []
        row_bot = grid[y + 1] if y + 1 < len(grid) else []

        row: HalfBlockRow = []
        for x in range(width):
            top = resolve(row_top[x]) if x < len(row_top) else None
            bot = resolve(row_bot[x]) if x < len(row_bot) else None

            if top is None and bot is None:
                row.append((" ", None, None))
            elif top is not None and bot is None:
                row.append(("▀", top, None))
            elif top is None and bot is not None:
                row.append(("▄", bot, None))
            elif top == bot:
                row.append(("█", top, None))
            else:
                # top pixel = fg (upper half), bot pixel = bg (lower half)
                row.append(("▀", top, bot))

        rows.append(row)

    return rows


def render_to_rich_text(
    converted: HalfBlockRows,
    default_bg: Optional[str] = None,
    center_width: int = 0,
) -> Text:
    """Convert half-block rows to a Rich Text object for Textual widgets.

    Args:
        converted: Output of convert_pixels().
        default_bg: Background color for transparent bg cells.
        center_width: If > 0, center each row within this many columns.
    """
    text = Text()
    for i, row in enumerate(converted):
        if center_width > 0 and len(row) < center_width:
            pad = (center_width - len(row)) // 2
            text.append(" " * pad)
        for char, fg, bg in row:
            if fg is None and bg is None:
                text.append(char)
            else:
                style = Style(
                    color=fg,
                    bgcolor=bg or default_bg,
                )
                text.append(char, style=style)
        if i < len(converted) - 1:
            text.append("\n")
    return text


# ---------------------------------------------------------------------------
# Color palettes — one per base coat color
# ---------------------------------------------------------------------------

# Palette keys used in pixel grids:
#   "fur"   — main body color
#   "shade" — slightly darkened fur (accents, eye outlines, edge shadows)
#   "dark"  — outline / dark details (ears, back)
#   "belly" — lighter underside
#   "pupil" — eye pupil (always near-black for contrast on any fur color)
#   "eye"   — eye gleam / highlight (always bright white)
#   "nose"  — nose / mouth
#   "ear"   — inner ear
#   "paw"   — feet
#    T  — protruding fur wisps (same color as fur, excluded from patterns)
#   "white" — white markings (for patterns / roan)

PALETTES: dict[str, dict[str, str]] = {
    "BLACK": {
        "fur":   "#444444",
        "shade": "#3a3a3a",
        "dark":  "#262626",
        "belly": "#585858",
        "pupil": "#121212",
        "eye":   "#ffffff",
        "nose":  "#808080",
        "ear":   "#4e4e4e",
        "paw":   "#303030",
        "tooth": "#c0c0c0",
        "white": "#d0d0d0",
        "blush": "#d75f5f",
        "tear":  "#05bce1",
         T:     "#444444",
    },
    "CHOCOLATE": {
        "fur":   "#875f00",
        "shade": "#8b4a00",
        "dark":  "#870000",
        "belly": "#ffaf5f",
        "pupil": "#121212",
        "eye":   "#ffffff",
        "nose":  "#af8787",
        "ear":   "#d75f5f",
        "paw":   "#d75f00",
        "tooth": "#c0c0c0",
        "white": "#d0d0d0",
        "blush": "#ff8787",
        "tear":  "#05bce1",
         T:     "#875f00",
    },
    "GOLDEN": {
        "fur":   "#ffd700",
        "shade": "#d4a800",
        "dark":  "#af8700",
        "belly": "#ffff5f",
        "pupil": "#121212",
        "eye":   "#ffffff",
        "nose":  "#d7af87",
        "ear":   "#d7af00",
        "paw":   "#af8700",
        "tooth": "#c0c0c0",
        "white": "#d0d0d0",
        "blush": "#ff8787",
        "tear":  "#05bce1",
         T:     "#ffd700",
    },
    "CREAM": {
        "fur":   "#ffffaf",
        "shade": "#e6d0a8",
        "dark":  "#d7af87",
        "belly": "#ffffd7",
        "pupil": "#121212",
        "eye":   "#ffffff",
        "nose":  "#ffd7d7",
        "ear":   "#ffd7af",
        "paw":   "#d7af87",
        "tooth": "#c0c0c0",
        "white": "#d0d0d0",
        "blush": "#ff5fd7",
        "tear":  "#05bce1",
         T:     "#ffffaf",
    },
    "BLUE": {
        "fur":   "#5fd7ff",
        "shade": "#5a7a9a",
        "dark":  "#3a5a7a",
        "belly": "#afafff",
        "pupil": "#121212",
        "eye":   "#ffffff",
        "nose":  "#8a9aaa",
        "ear":   "#6a8aaa",
        "paw":   "#4a6a8a",
        "tooth": "#c0c0c0",
        "white": "#d0d0d0",
        "blush": "#d75f5f",
        "tear":  "#05bce1",
         T:     "#5fd7ff",
    },
    "LILAC": {
        "fur":   "#ffafff",
        "shade": "#b888c8",
        "dark":  "#8a60a0",
        "belly": "#e8c8f8",
        "pupil": "#121212",
        "eye":   "#ffffff",
        "nose":  "#c8a8d8",
        "ear":   "#b090c0",
        "paw":   "#9070a8",
        "tooth": "#c0c0c0",
        "white": "#d0d0d0",
        "blush": "#ff5fd7",
        "tear":  "#117d92",
         T:     "#ffafff",
    },
    "SAFFRON": {
        "fur":   "#ff8700",
        "shade": "#c87830",
        "dark":  "#a06020",
        "belly": "#e8a050",
        "pupil": "#121212",
        "eye":   "#ffffff",
        "nose":  "#d09060",
        "ear":   "#c08040",
        "paw":   "#b07838",
        "tooth": "#c0c0c0",
        "white": "#d0d0d0",
        "blush": "#ff8787",
        "tear":  "#05bce1",
         T:     "#ff8700",
    },
    "SMOKE": {
        "fur":   "#9e9e9e",
        "shade": "#787878",
        "dark":  "#606060",
        "belly": "#a0a0a0",
        "pupil": "#121212",
        "eye":   "#ffffff",
        "nose":  "#988890",
        "ear":   "#908088",
        "paw":   "#808080",
        "tooth": "#c0c0c0",
        "white": "#d0d0d0",
        "blush": "#ff5fd7",
        "tear":  "#05bce1",
         T:     "#9e9e9e",
    },
}


# ---------------------------------------------------------------------------
# Pixel grid scaling (for close zoom)
# ---------------------------------------------------------------------------

def scale_pixel_grid(grid: PixelGrid, factor: int) -> PixelGrid:
    """Scale a pixel grid by an integer factor (2 = double size)."""
    scaled: PixelGrid = []
    for row in grid:
        scaled_row = []
        for pixel in row:
            scaled_row.extend([pixel] * factor)
        for _ in range(factor):
            scaled.append(list(scaled_row))
    return scaled


# ---------------------------------------------------------------------------
# Compact sprite encoding (for hand-crafted close-zoom sprites)
# ---------------------------------------------------------------------------

CharMap = dict[str, Optional[str]]


def decode_sprite(
    lines: list[str], char_map: CharMap, width: int = 0,
) -> PixelGrid:
    """Decode a compact single-char-per-pixel sprite into a PixelGrid.

    Each character in *lines* is looked up in *char_map* to produce a palette
    key (or None for transparent).  This keeps large close-zoom grids compact
    in source.

    If *width* is given, every row is right-padded with ``None`` to that width,
    ensuring uniform dimensions even when trailing transparent pixels are
    omitted from the source strings.
    """
    grid: PixelGrid = []
    for line in lines:
        row = [char_map.get(c) for c in line]
        if width and len(row) < width:
            row.extend([None] * (width - len(row)))
        grid.append(row)
    return grid


def mirror_grid(grid: PixelGrid) -> PixelGrid:
    """Mirror a pixel grid horizontally (flip left/right)."""
    return [list(reversed(row)) for row in grid]


def build_mirrored_dict(
    right_sprites: dict[str, PixelGrid],
) -> dict[str, PixelGrid]:
    """Build a dict containing both right- and left-facing variants.

    *right_sprites* keys must contain ``_right``.  For each entry a mirrored
    ``_left`` variant is generated automatically.
    """
    result: dict[str, PixelGrid] = {}
    for key, grid in right_sprites.items():
        result[key] = grid
        result[key.replace("_right", "_left")] = mirror_grid(grid)
    return result
