"""Half-block pixel rendering engine and pig sprite/palette definitions.

Unicode half-block characters (▀▄█ ) give 2 vertical pixels per terminal cell.
All sprites — farm, portraits, UI — share the convert_pixels() pipeline.
"""

from typing import Optional

from rich.text import Text
from rich.style import Style


# ---------------------------------------------------------------------------
# Core converter
# ---------------------------------------------------------------------------

# Type aliases for clarity
PixelGrid = list[list[Optional[str]]]  # 2D grid of palette keys or None (transparent)
HalfBlockRow = list[tuple[str, Optional[str], Optional[str]]]  # (char, fg, bg)
HalfBlockRows = list[HalfBlockRow]

# Transparent sentinel
T = None


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
) -> Text:
    """Convert half-block rows to a Rich Text object for Textual widgets.

    Args:
        converted: Output of convert_pixels().
        default_bg: Background color for transparent bg cells.
    """
    text = Text()
    for i, row in enumerate(converted):
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
#   "dark"  — outline / dark details (ears, back)
#   "belly" — lighter underside
#   "eye"   — eye color
#   "nose"  — nose / mouth
#   "ear"   — inner ear
#   "paw"   — feet
#   "white" — white markings (for patterns / roan)

PALETTES: dict[str, dict[str, str]] = {
    "BLACK": {
        "fur":   "grey23",
        "dark":  "grey15",
        "belly": "grey35",
        "eye":   "white",
        "nose":  "grey50",
        "ear":   "grey30",
        "paw":   "grey19",
        "white": "grey82",
    },
    "CHOCOLATE": {
        "fur":   "orange4",
        "dark":  "dark_red",
        "belly": "sandy_brown",
        "eye":   "white",
        "nose":  "rosy_brown",
        "ear":   "indian_red",
        "paw":   "sienna",
        "white": "grey82",
    },
    "GOLDEN": {
        "fur":   "gold1",
        "dark":  "dark_goldenrod",
        "belly": "light_goldenrod1",
        "eye":   "white",
        "nose":  "tan",
        "ear":   "goldenrod",
        "paw":   "dark_goldenrod",
        "white": "grey82",
    },
    "CREAM": {
        "fur":   "wheat1",
        "dark":  "tan",
        "belly": "lemon_chiffon1",
        "eye":   "white",
        "nose":  "misty_rose1",
        "ear":   "navajo_white1",
        "paw":   "tan",
        "white": "grey82",
    },
}


# ---------------------------------------------------------------------------
# Pig pixel art — normal zoom (7 wide x 6 tall -> 7 x 3 half-block chars)
# ---------------------------------------------------------------------------

# Palette keys used:  fur, dark, belly, eye, nose, ear, paw, T(ransparent)

# fmt: off

# --- Adult sprites (7w x 6h pixels) ---

PIG_PIXELS_ADULT = {
    "idle_right": [
        [ T,    T,    "ear","dark","dark", T,    T   ],
        [ T,   "dark","fur", "fur","fur", "dark", T   ],
        ["dark","fur","eye", "fur","nose","fur", "dark"],
        [ T,   "dark","fur", "fur","fur", "fur", "dark"],
        [ T,   "dark","belly","belly","belly","fur","dark"],
        [ T,    T,   "paw", T,   "paw", T,    T   ],
    ],
    "idle_left": [
        [ T,    T,   "dark","dark","ear", T,    T   ],
        [ T,   "dark","fur", "fur","fur", "dark", T   ],
        ["dark","fur","nose","fur","eye", "fur", "dark"],
        ["dark","fur", "fur","fur","fur", "dark", T   ],
        ["dark","fur","belly","belly","belly","dark", T   ],
        [ T,    T,   "paw", T,   "paw", T,    T   ],
    ],
    "walking_right": [
        [ T,    T,   "ear","dark","dark", T,    T   ],
        [ T,   "dark","fur", "fur","fur", "dark", T   ],
        ["dark","fur","eye", "fur","nose","fur", "dark"],
        [ T,   "dark","fur", "fur","fur", "fur", "dark"],
        [ T,   "dark","belly","belly","belly","fur","dark"],
        [ T,   "paw", T,    T,    T,   "paw", T   ],
    ],
    "walking_left": [
        [ T,    T,   "dark","dark","ear", T,    T   ],
        [ T,   "dark","fur", "fur","fur", "dark", T   ],
        ["dark","fur","nose","fur","eye", "fur", "dark"],
        ["dark","fur", "fur","fur","fur", "dark", T   ],
        ["dark","fur","belly","belly","belly","dark", T   ],
        [ T,   "paw", T,    T,    T,   "paw", T   ],
    ],
    "eating_right": [
        [ T,    T,   "ear","dark","dark", T,    T   ],
        [ T,   "dark","fur", "fur","fur", "dark", T   ],
        ["dark","fur","eye", "fur","eye", "fur", "dark"],
        [ T,   "dark","fur","nose","fur", "fur", "dark"],
        [ T,   "dark","belly","belly","belly","fur","dark"],
        [ T,    T,   "paw", T,   "paw", T,    T   ],
    ],
    "eating_left": [
        [ T,    T,   "dark","dark","ear", T,    T   ],
        [ T,   "dark","fur", "fur","fur", "dark", T   ],
        ["dark","fur","eye", "fur","eye", "fur", "dark"],
        ["dark","fur", "fur","nose","fur", "dark", T   ],
        ["dark","fur","belly","belly","belly","dark", T   ],
        [ T,    T,   "paw", T,   "paw", T,    T   ],
    ],
    "sleeping_right": [
        [ T,    T,   "ear","dark","dark", T,    T   ],
        [ T,   "dark","fur", "fur","fur", "dark", T   ],
        ["dark","fur","dark","fur","dark","fur", "dark"],
        [ T,   "dark","fur", "fur","fur", "fur", "dark"],
        [ T,   "dark","belly","belly","belly","fur","dark"],
        [ T,    T,   "paw", T,   "paw", T,    T   ],
    ],
    "sleeping_left": [
        [ T,    T,   "dark","dark","ear", T,    T   ],
        [ T,   "dark","fur", "fur","fur", "dark", T   ],
        ["dark","fur","dark","fur","dark","fur", "dark"],
        ["dark","fur", "fur","fur","fur", "dark", T   ],
        ["dark","fur","belly","belly","belly","dark", T   ],
        [ T,    T,   "paw", T,   "paw", T,    T   ],
    ],
    "happy_right": [
        [ T,    T,   "ear","dark","dark", T,    T   ],
        [ T,   "dark","fur", "fur","fur", "dark", T   ],
        ["dark","fur","eye", "fur","eye", "fur", "dark"],
        [ T,   "dark","fur","nose","fur", "fur", "dark"],
        [ T,   "dark","belly","belly","belly","fur","dark"],
        [ T,    T,   "paw", T,   "paw", T,    T   ],
    ],
    "happy_left": [
        [ T,    T,   "dark","dark","ear", T,    T   ],
        [ T,   "dark","fur", "fur","fur", "dark", T   ],
        ["dark","fur","eye", "fur","eye", "fur", "dark"],
        ["dark","fur", "fur","nose","fur", "dark", T   ],
        ["dark","fur","belly","belly","belly","dark", T   ],
        [ T,    T,   "paw", T,   "paw", T,    T   ],
    ],
    "sad_right": [
        [ T,    T,   "ear","dark","dark", T,    T   ],
        [ T,   "dark","fur", "fur","fur", "dark", T   ],
        ["dark","fur","eye", "fur","eye", "fur", "dark"],
        [ T,   "dark","fur","nose","fur", "fur", "dark"],
        [ T,   "dark","belly","belly","belly","fur","dark"],
        [ T,    T,   "paw", T,   "paw", T,    T   ],
    ],
    "sad_left": [
        [ T,    T,   "dark","dark","ear", T,    T   ],
        [ T,   "dark","fur", "fur","fur", "dark", T   ],
        ["dark","fur","eye", "fur","eye", "fur", "dark"],
        ["dark","fur", "fur","nose","fur", "dark", T   ],
        ["dark","fur","belly","belly","belly","dark", T   ],
        [ T,    T,   "paw", T,   "paw", T,    T   ],
    ],
}

# --- Baby sprites (5w x 4h pixels) ---

PIG_PIXELS_BABY = {
    "idle_right": [
        [ T,   "ear","dark","dark", T   ],
        ["dark","eye","fur","nose","dark"],
        ["dark","belly","belly","fur","dark"],
        [ T,   "paw", T,  "paw", T   ],
    ],
    "idle_left": [
        [ T,   "dark","dark","ear", T   ],
        ["dark","nose","fur","eye","dark"],
        ["dark","fur","belly","belly","dark"],
        [ T,   "paw", T,  "paw", T   ],
    ],
    "walking_right": [
        [ T,   "ear","dark","dark", T   ],
        ["dark","eye","fur","nose","dark"],
        ["dark","belly","belly","fur","dark"],
        ["paw", T,    T,  "paw", T   ],
    ],
    "walking_left": [
        [ T,   "dark","dark","ear", T   ],
        ["dark","nose","fur","eye","dark"],
        ["dark","fur","belly","belly","dark"],
        [ T,   "paw", T,    T,  "paw"],
    ],
    "sleeping_right": [
        [ T,   "ear","dark","dark", T   ],
        ["dark","dark","fur","dark","dark"],
        ["dark","belly","belly","fur","dark"],
        [ T,   "paw", T,  "paw", T   ],
    ],
    "sleeping_left": [
        [ T,   "dark","dark","ear", T   ],
        ["dark","dark","fur","dark","dark"],
        ["dark","fur","belly","belly","dark"],
        [ T,   "paw", T,  "paw", T   ],
    ],
}

# --- Close zoom sprites (14w x 12h pixels -> 14 x 6 half-block chars) ---

PIG_PIXELS_CLOSE_ADULT = {
    "idle_right": [
        [ T,  T,  T,  T, "ear","ear","dark","dark","dark","dark", T,  T,  T,  T ],
        [ T,  T,  T, "dark","ear","dark","fur","fur","fur","dark","dark", T,  T,  T ],
        [ T,  T, "dark","fur","fur","fur","fur","fur","fur","fur","fur","dark", T,  T ],
        [ T, "dark","fur","fur","eye","eye","fur","fur","nose","nose","fur","fur","dark", T ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T, "dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark", T ],
        [ T, "dark","dark","fur","fur","fur","fur","fur","fur","fur","fur","dark","dark", T ],
        [ T, "dark","belly","belly","belly","belly","belly","belly","belly","fur","fur","dark", T, T ],
        [ T, "dark","belly","belly","belly","belly","belly","belly","belly","fur","fur","dark", T, T ],
        [ T, "dark","dark","belly","belly","belly","belly","belly","belly","fur","dark","dark", T, T ],
        [ T,  T, "paw","paw", T,  T,  T,  T, "paw","paw", T,  T,  T,  T ],
        [ T,  T, "paw","paw", T,  T,  T,  T, "paw","paw", T,  T,  T,  T ],
    ],
    "idle_left": [
        [ T,  T,  T,  T, "dark","dark","dark","dark","ear","ear", T,  T,  T,  T ],
        [ T,  T,  T, "dark","dark","fur","fur","fur","dark","ear","dark", T,  T,  T ],
        [ T,  T, "dark","fur","fur","fur","fur","fur","fur","fur","fur","dark", T,  T ],
        [ T, "dark","fur","fur","nose","nose","fur","fur","eye","eye","fur","fur","dark", T ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T, "dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark", T ],
        [ T, "dark","dark","fur","fur","fur","fur","fur","fur","fur","fur","dark","dark", T ],
        [ T,  T, "dark","fur","fur","belly","belly","belly","belly","belly","belly","dark", T, T ],
        [ T,  T, "dark","fur","fur","belly","belly","belly","belly","belly","belly","dark", T, T ],
        [ T,  T, "dark","dark","fur","belly","belly","belly","belly","belly","dark","dark", T, T ],
        [ T,  T,  T,  T, "paw","paw", T,  T, "paw","paw", T,  T,  T,  T ],
        [ T,  T,  T,  T, "paw","paw", T,  T, "paw","paw", T,  T,  T,  T ],
    ],
}

# fmt: on


# ---------------------------------------------------------------------------
# Helper: get pixel sprite for a given state + zoom
# ---------------------------------------------------------------------------

def get_pig_pixel_sprite(
    state: str,
    direction: str,
    is_baby: bool = False,
    close_zoom: bool = False,
) -> PixelGrid:
    """Look up the pixel grid for a pig sprite.

    Falls back gracefully: close->normal, missing state->idle.
    """
    key = f"{state}_{direction}"

    if close_zoom and not is_baby:
        sprites = PIG_PIXELS_CLOSE_ADULT
        if key in sprites:
            return sprites[key]
        # Fallback to idle at close zoom
        fallback = f"idle_{direction}"
        if fallback in sprites:
            return sprites[fallback]

    # Normal zoom
    sprites = PIG_PIXELS_BABY if is_baby else PIG_PIXELS_ADULT
    if key in sprites:
        return sprites[key]

    fallback = f"idle_{direction}"
    return sprites.get(fallback, sprites["idle_right"])
