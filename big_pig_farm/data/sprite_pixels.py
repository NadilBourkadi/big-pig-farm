"""Half-block pixel rendering engine and pig sprite/palette definitions.

Unicode half-block characters (▀▄█ ) give 2 vertical pixels per terminal cell.
All sprites — farm, portraits, UI — share the convert_pixels() pipeline.
"""

import copy
import hashlib
import random as _random
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

# Animation timing: ticks per frame for each animated display state.
# States not listed here are static (single frame).
ANIM_TICKS_PER_FRAME: dict[str, int] = {
    "walking": 3,
    "eating": 4,
    "happy": 3,
    "sleeping": 10,
}


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
        "fur":   "grey27",
        "dark":  "grey15",
        "belly": "grey35",
        "pupil": "grey7",
        "eye":   "#ffffff",
        "nose":  "grey50",
        "ear":   "grey30",
        "paw":   "grey19",
         T:  "grey27",
        "tooth": "white",
        "white": "grey82",
        "blush": "indian_red",
    },
    "CHOCOLATE": {
        "fur":   "orange4",
        "dark":  "dark_red",
        "belly": "sandy_brown",
        "pupil": "grey7",
        "eye":   "#ffffff",
        "nose":  "rosy_brown",
        "ear":   "indian_red",
        "paw":   "dark_orange3",
         T:  "orange4",
        "tooth": "white",
        "white": "grey82",
        "blush": "light_coral",
    },
    "GOLDEN": {
        "fur":   "gold1",
        "dark":  "dark_goldenrod",
        "belly": "light_goldenrod1",
        "pupil": "grey7",
        "eye":   "#ffffff",
        "nose":  "tan",
        "ear":   "gold3",
        "paw":   "dark_goldenrod",
         T:  "gold1",
        "tooth": "white",
        "white": "grey82",
        "blush": "light_coral",
    },
    "CREAM": {
        "fur":   "wheat1",
        "dark":  "tan",
        "belly": "cornsilk1",
        "pupil": "grey7",
        "eye":   "#ffffff",
        "nose":  "misty_rose1",
        "ear":   "navajo_white1",
        "paw":   "tan",
         T:  "wheat1",
        "tooth": "white",
        "white": "grey82",
        "blush": "hot_pink",
    },
}


# ---------------------------------------------------------------------------
# Pig pixel art — normal zoom (14 wide x 8 tall -> 14 x 4 half-block chars)
#
# Guinea pigs are potato-shaped: much wider than tall, smooth rounded back,
# tiny ear nub, prominent dark+gleam eye near the front, nose at the tip,
# continuous dark outline, barely-visible paws, belly stripe underneath.
# "right" = facing right (head on the right side of the sprite).
# ---------------------------------------------------------------------------

# Palette keys used:  fur, dark, belly, eye, nose, ear, paw, T(ransparent)

# fmt: off

# --- Adult sprites (14w x 8h pixels) ---

PIG_PIXELS_ADULT = {
    "idle_right": [
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark","ear","dark", T,   T  ],
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","fur","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","eye","eye","pupil","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","eye","pupil","pupil","nose","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "idle_left": [
        [ T,   T,  "dark","ear","dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,  "dark","fur","fur","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","pupil","eye","eye","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","nose","pupil","pupil","eye","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "walking_right": [
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark","ear","dark", T,   T  ],
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","fur","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","eye","eye","pupil","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","eye","pupil","pupil","nose","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,  "paw", T,   T,   T,   T,   T,   T,   T,   T,  "paw", T,   T  ],
    ],
    "walking_left": [
        [ T,   T,  "dark","ear","dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,  "dark","fur","fur","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","pupil","eye","eye","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","nose","pupil","pupil","eye","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,  "paw", T,   T,   T,   T,   T,   T,   T,   T,  "paw", T,   T  ],
    ],
    "eating_right": [
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark","ear","dark", T,   T  ],
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","fur","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","dark","dark","fur","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","nose","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "eating_left": [
        [ T,   T,  "dark","ear","dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,  "dark","fur","fur","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","fur","dark","dark","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","nose","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "sleeping_right": [
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark","ear","dark", T,   T  ],
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","fur","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","dark","dark","fur","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "sleeping_left": [
        [ T,   T,  "dark","ear","dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,  "dark","fur","fur","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","fur","dark","dark","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "happy_right": [
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark","ear","dark", T,   T  ],
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","fur","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","eye","eye","pupil","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","eye","pupil","pupil","nose","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "happy_left": [
        [ T,   T,  "dark","ear","dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,  "dark","fur","fur","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","pupil","eye","eye","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","nose","pupil","pupil","eye","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "sad_right": [
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark","ear","dark", T,   T  ],
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","fur","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","eye","eye","pupil","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","eye","pupil","pupil","nose","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "sad_left": [
        [ T,   T,  "dark","ear","dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,  "dark","fur","fur","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","pupil","eye","eye","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","nose","pupil","pupil","eye","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    # --- Frame 1 variants (animation alternates) ---
    # Walking: body bobs down 1px + leans forward + ear flattens (rocking waddle)
    # Frame 0 = up stride (centered, paws spread), frame 1 = down stride (forward lean, paws tucked)
    "walking_right_1": [
        [ T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark", T,  "dark", T,   T  ],
        [ T,   T,   T,   T,  "dark","dark","dark","dark","fur","fur","ear","fur","fur","dark"],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","eye","eye","pupil","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","eye","pupil","pupil","nose","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,   T,  "dark","fur","fur","fur","fur","fur","fur","fur","belly","belly","dark", T  ],
        [ T,   T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T  ],
    ],
    "walking_left_1": [
        [ T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,   T,  "dark", T,  "dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        ["dark","fur","fur","ear","fur","fur","dark","dark","dark","dark", T,   T,   T,   T  ],
        ["dark","fur","pupil","eye","eye","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","nose","pupil","pupil","eye","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        [ T,  "dark","belly","belly","fur","fur","fur","fur","fur","fur","fur","dark", T,   T  ],
        [ T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T,   T  ],
    ],
    # Eating: ear flattens + whole face dips (closed eyes shift down 1 row) + nose dips
    "eating_right_1": [
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark", T,  "dark", T,   T  ],
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","ear","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","dark","dark","fur","fur","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","nose","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "eating_left_1": [
        [ T,   T,  "dark", T,  "dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,  "dark","fur","ear","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","fur","dark","dark","fur","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","nose","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    # Happy (playing): hop up 1px + ear merges into head + paws spread (jumping pose)
    "happy_right_1": [
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","ear","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","eye","eye","pupil","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","eye","pupil","pupil","nose","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,  "paw", T,   T,   T,   T,   T,   T,   T,   T,  "paw", T,   T  ],
        [ T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T  ],
    ],
    "happy_left_1": [
        [ T,  "dark","fur","ear","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","pupil","eye","eye","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","nose","pupil","pupil","eye","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,  "paw", T,   T,   T,   T,   T,   T,   T,   T,  "paw", T,   T  ],
        [ T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T  ],
    ],
    # Sleeping: belly + underside expand outward on both sides (visible body puffing)
    "sleeping_right_1": [
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark","ear","dark", T,   T  ],
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","fur","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","dark","dark","fur","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        ["dark","belly","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","belly","dark"],
        [ T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","dark", T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "sleeping_left_1": [
        [ T,   T,  "dark","ear","dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,  "dark","fur","fur","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","fur","dark","dark","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        ["dark","belly","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","belly","dark"],
        [ T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","dark", T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
}

# --- Baby sprites (8w x 6h pixels) ---

PIG_PIXELS_BABY = {
    "idle_right": [
        [ T,   T,   T,   T,  "dark","ear","dark", T  ],
        [ T,  "dark","dark","dark","fur","fur","fur","dark"],
        [ T,  "dark","fur","fur","eye","pupil","fur","dark"],
        ["dark","belly","fur","fur","eye","eye","nose","dark"],
        [ T,  "dark","belly","belly","belly","belly","dark", T  ],
        [ T,   T,  "paw", T,   T,  "paw", T,   T  ],
    ],
    "idle_left": [
        [ T,  "dark","ear","dark", T,   T,   T,   T  ],
        ["dark","fur","fur","fur","dark","dark","dark", T  ],
        ["dark","fur","pupil","eye","fur","fur","dark", T  ],
        ["dark","nose","eye","eye","fur","fur","belly","dark"],
        [ T,  "dark","belly","belly","belly","belly","dark", T  ],
        [ T,   T,  "paw", T,   T,  "paw", T,   T  ],
    ],
    "walking_right": [
        [ T,   T,   T,   T,  "dark","ear","dark", T  ],
        [ T,  "dark","dark","dark","fur","fur","fur","dark"],
        [ T,  "dark","fur","fur","eye","pupil","fur","dark"],
        ["dark","belly","fur","fur","eye","eye","nose","dark"],
        [ T,  "dark","belly","belly","belly","belly","dark", T  ],
        [ T,  "paw", T,   T,   T,   T,  "paw", T  ],
    ],
    "walking_left": [
        [ T,  "dark","ear","dark", T,   T,   T,   T  ],
        ["dark","fur","fur","fur","dark","dark","dark", T  ],
        ["dark","fur","pupil","eye","fur","fur","dark", T  ],
        ["dark","nose","eye","eye","fur","fur","belly","dark"],
        [ T,  "dark","belly","belly","belly","belly","dark", T  ],
        [ T,  "paw", T,   T,   T,   T,  "paw", T  ],
    ],
    "sleeping_right": [
        [ T,   T,   T,   T,  "dark","ear","dark", T  ],
        [ T,  "dark","dark","dark","fur","fur","fur","dark"],
        [ T,  "dark","fur","fur","dark","dark","fur","dark"],
        ["dark","belly","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","belly","belly","belly","dark", T  ],
        [ T,   T,  "paw", T,   T,  "paw", T,   T  ],
    ],
    "sleeping_left": [
        [ T,  "dark","ear","dark", T,   T,   T,   T  ],
        ["dark","fur","fur","fur","dark","dark","dark", T  ],
        ["dark","fur","dark","dark","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","belly","dark"],
        [ T,  "dark","belly","belly","belly","belly","dark", T  ],
        [ T,   T,  "paw", T,   T,  "paw", T,   T  ],
    ],
    # --- Frame 1 variants (animation alternates) ---
    # Walking: ear bounce (flattens into head) + paws together
    "walking_right_1": [
        [ T,   T,   T,   T,  "dark", T,  "dark", T  ],
        [ T,  "dark","dark","dark","fur","ear","fur","dark"],
        [ T,  "dark","fur","fur","eye","pupil","fur","dark"],
        ["dark","belly","fur","fur","eye","eye","nose","dark"],
        [ T,  "dark","belly","belly","belly","belly","dark", T  ],
        [ T,   T,  "paw", T,   T,  "paw", T,   T  ],
    ],
    "walking_left_1": [
        [ T,  "dark", T,  "dark", T,   T,   T,   T  ],
        ["dark","fur","ear","fur","dark","dark","dark", T  ],
        ["dark","fur","pupil","eye","fur","fur","dark", T  ],
        ["dark","nose","eye","eye","fur","fur","belly","dark"],
        [ T,  "dark","belly","belly","belly","belly","dark", T  ],
        [ T,   T,  "paw", T,   T,  "paw", T,   T  ],
    ],
    # Sleeping: body + underside expand outward (breathing)
    "sleeping_right_1": [
        [ T,   T,   T,   T,  "dark","ear","dark", T  ],
        [ T,  "dark","dark","dark","fur","fur","fur","dark"],
        [ T,  "dark","fur","fur","dark","dark","fur","dark"],
        ["dark","belly","belly","fur","fur","fur","belly","dark"],
        ["dark","belly","belly","belly","belly","belly","belly","dark"],
        [ T,   T,  "paw", T,   T,  "paw", T,   T  ],
    ],
    "sleeping_left_1": [
        [ T,  "dark","ear","dark", T,   T,   T,   T  ],
        ["dark","fur","fur","fur","dark","dark","dark", T  ],
        ["dark","fur","dark","dark","fur","fur","dark", T  ],
        ["dark","belly","fur","fur","fur","belly","belly","dark"],
        ["dark","belly","belly","belly","belly","belly","belly","dark"],
        [ T,   T,  "paw", T,   T,  "paw", T,   T  ],
    ],
}

# --- Far-zoom adult sprites (7w x 6h pixels -> 7x3 half-block chars) ---

PIG_PIXELS_FAR_ADULT = {
    "idle_right": [
        [ T,   T,  "dark","dark","dark","ear","dark"],
        [ T,  "dark","fur", "fur", "fur","fur","dark"],
        ["dark","fur", "fur", "fur","eye","pupil","dark"],
        ["dark","fur", "fur", "fur", "fur","nose","dark"],
        [ T,  "dark","belly","belly","belly","dark", T  ],
        [ T,   T,  "paw", T,  "paw", T,   T  ],
    ],
    "idle_left": [
        ["dark","ear","dark","dark","dark", T,   T  ],
        ["dark","fur", "fur", "fur","fur","dark", T  ],
        ["dark","pupil","eye","fur", "fur", "fur","dark"],
        ["dark","nose","fur", "fur", "fur", "fur","dark"],
        [ T,  "dark","belly","belly","belly","dark", T  ],
        [ T,   T,  "paw", T,  "paw", T,   T  ],
    ],
    # Walking frame 1: body bobs down (top row empty, paws tucked)
    "walking_right_1": [
        [ T,   T,   T,   T,   T,   T,   T  ],
        [ T,   T,  "dark","dark","dark","ear","dark"],
        [ T,  "dark","fur", "fur","eye","pupil","dark"],
        ["dark","fur", "fur", "fur", "fur","nose","dark"],
        [ T,  "dark","fur", "belly","belly","dark", T  ],
        [ T,  "dark","belly","belly","belly","dark", T  ],
    ],
    "walking_left_1": [
        [ T,   T,   T,   T,   T,   T,   T  ],
        ["dark","ear","dark","dark","dark", T,   T  ],
        ["dark","pupil","eye","fur", "fur","dark", T  ],
        ["dark","nose","fur", "fur", "fur", "fur","dark"],
        [ T,  "dark","belly","belly","fur","dark", T  ],
        [ T,  "dark","belly","belly","belly","dark", T  ],
    ],
    # Sleeping frame 1: belly widens (breathing)
    "sleeping_right_1": [
        [ T,   T,  "dark","dark","dark","ear","dark"],
        [ T,  "dark","fur", "fur", "fur","fur","dark"],
        ["dark","fur", "fur", "fur","dark","dark","dark"],
        ["dark","fur", "fur", "fur", "fur","fur","dark"],
        ["dark","belly","belly","belly","belly","belly","dark"],
        [ T,   T,  "paw", T,  "paw", T,   T  ],
    ],
    "sleeping_left_1": [
        ["dark","ear","dark","dark","dark", T,   T  ],
        ["dark","fur", "fur", "fur","fur","dark", T  ],
        ["dark","dark","dark","fur", "fur", "fur","dark"],
        ["dark","fur", "fur", "fur", "fur", "fur","dark"],
        ["dark","belly","belly","belly","belly","belly","dark"],
        [ T,   T,  "paw", T,  "paw", T,   T  ],
    ],
}

# --- Far-zoom baby sprites (5w x 4h pixels -> 5x2 half-block chars) ---

PIG_PIXELS_FAR_BABY = {
    "idle_right": [
        [ T,  "dark","dark","ear","dark"],
        ["dark","fur","eye","pupil","dark"],
        ["dark","fur", "fur","nose","dark"],
        [ T,  "dark","belly","dark", T  ],
    ],
    "idle_left": [
        ["dark","ear","dark","dark", T  ],
        ["dark","pupil","eye","fur","dark"],
        ["dark","nose","fur", "fur","dark"],
        [ T,  "dark","belly","dark", T  ],
    ],
    # Walking frame 1: body bobs down
    "walking_right_1": [
        [ T,   T,   T,   T,   T  ],
        [ T,  "dark","dark","ear","dark"],
        ["dark","fur","eye","pupil","dark"],
        ["dark","fur", "fur","nose","dark"],
    ],
    "walking_left_1": [
        [ T,   T,   T,   T,   T  ],
        ["dark","ear","dark","dark", T  ],
        ["dark","pupil","eye","fur","dark"],
        ["dark","nose","fur", "fur","dark"],
    ],
}

# fmt: on


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
# Helper: get pixel sprite for a given state + zoom
# ---------------------------------------------------------------------------

def get_pig_pixel_sprite(
    state: str,
    direction: str,
    is_baby: bool = False,
    close_zoom: bool = False,
    far_zoom: bool = False,
    frame: int = 0,
) -> PixelGrid:
    """Look up the pixel grid for a pig sprite.

    Falls back gracefully: missing state -> idle, missing frame -> frame 0.
    Close zoom auto-scales the normal sprite by 2x.
    Far zoom returns tiny 7x6 (adult) or 5x4 (baby) sprites.
    """
    key = f"{state}_{direction}"

    if far_zoom:
        sprites = PIG_PIXELS_FAR_BABY if is_baby else PIG_PIXELS_FAR_ADULT
        if frame > 0:
            anim_key = f"{key}_{frame}"
            if anim_key in sprites:
                return sprites[anim_key]
        if key not in sprites:
            key = f"idle_{direction}"
        return sprites.get(key, sprites["idle_right"])

    # Normal zoom
    sprites = PIG_PIXELS_BABY if is_baby else PIG_PIXELS_ADULT

    # Try animated frame variant first
    if frame > 0:
        anim_key = f"{key}_{frame}"
        if anim_key in sprites:
            grid = sprites[anim_key]
            if close_zoom:
                return scale_pixel_grid(grid, 2)
            return grid

    if key not in sprites:
        key = f"idle_{direction}"
    grid = sprites.get(key, sprites["idle_right"])

    if close_zoom:
        return scale_pixel_grid(grid, 2)
    return grid


# ---------------------------------------------------------------------------
# Procedural pig portraits  (32 x 24 pixels -> 32 x 12 half-block chars)
# ---------------------------------------------------------------------------

# The 32x24 face template: a front-facing guinea pig head.
# Guinea pigs are WIDER than tall with puffy cheeks and fluffy fur.
# Key features that make it look like a guinea pig, not a potato:
#   - Irregular silhouette with fur tufts breaking the outline
#   - Prominent rounded ears on the sides with inner-ear detail
#   - Cartoonish eyes (3x3 white sclera with dark pupil center)
#   - Small distinct nose with nostrils + little mouth with teeth
#   - Fluffy cheek poufs that bulge outward
#   - Wisps of fur on top of head (rosette) using  T key
# Uses palette keys directly — pattern/intensity functions mutate them.
# fmt: off
_FACE_TEMPLATE: PixelGrid = [
    #  0      1      2      3      4      5      6      7      8      9     10     11     12     13     14     15     16     17     18     19     20     21     22     23     24     25     26     27     28     29     30     31
    [ T,     T,     T,     T,     T,     T,     T,     T, T,     T, T,     T,    "dark","dark","dark","dark","dark","dark","dark","dark", T,     T,     T, T,     T, T,     T,     T,     T,     T,     T,     T    ],  # 0  rosette tufts
    [ T,     T,     T,     T,     T,     T,     T, T,    "dark","dark","dark","dark","fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark","dark","dark","dark", T,     T, T,     T,     T,     T,     T,     T    ],  # 1  crown + tufts
    [ T,     T,     T,     T,     T,     T,    "dark","dark","fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark","dark", T,     T,     T,     T,     T,     T    ],  # 2  upper head
    [ T,     T,     T,     T,     T,    "dark","fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark", T,     T,     T,     T,     T    ],  # 3  forehead
    [ T,     T,     T,    "dark","ear", "ear","dark", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark","ear", "ear","dark", T,     T,     T    ],  # 4  ears start
    [ T,     T,    "dark","ear", "ear", "ear","dark", "fur", "fur","dark","dark","dark","dark","dark","fur", "fur", "fur", "fur","dark","dark","dark","dark","dark","fur", "fur","dark","ear", "ear", "ear","dark", T,     T    ],  # 5  above eyes (outline top)
    [ T,    "dark","ear", "ear", "ear","dark","fur",  "fur","dark", "eye", "eye","pupil","dark", "fur", "fur", "fur", "fur", "fur","dark", "eye", "eye","pupil","dark", "fur", "fur", "fur","dark","ear", "ear", "ear","dark", T    ],  # 6  eyes top (gleam + pupil)
    [ T,    "dark","ear", "ear","dark","dark","fur",  "fur","dark", "eye","pupil","pupil","dark", "fur", "fur", "fur", "fur", "fur","dark", "eye","pupil","pupil","dark", "fur", "fur", "fur","dark","dark","ear", "ear","dark", T    ],  # 7  eyes mid (pupil 2x2 lower)
    [ T,   "dark","dark","dark", T,   "dark","fur",  "fur","dark", "eye", "eye", "eye","dark", "fur", "fur", "fur", "fur", "fur","dark", "eye", "eye", "eye","dark", "fur", "fur", "fur","dark", T,   "dark","dark","dark", T    ],  # 8  eyes bottom (sclera + outline)
    [ T,     T,     T,     T,     T,   "dark","fur",  "fur", "fur","dark","dark","dark","dark", "fur", "fur", "fur", "fur", "fur", "fur","dark","dark","dark","dark", "fur", "fur", "fur","dark", T,     T,     T,     T,     T    ],  # 9  below eyes (outline bottom)
    [ T, T,     T,     T,    "dark","fur", "fur","blush","blush","fur", "fur", "fur", "fur", "fur","nose","nose","nose","nose","fur", "fur", "fur", "fur", "fur","blush","blush","fur", "fur","dark", T,     T,     T,     T],  # 10 cheeks + blush + nose top
    [ T, T,     T,     T,    "dark","fur", "fur",  "fur", "fur", "fur", "fur", "fur", "fur","nose","nose","nose","nose","nose","nose","fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark", T,     T,     T,     T],  # 11 nose pad
    [ T,     T,     T,     T,    "dark","fur", "fur",  "fur", "fur", "fur", "fur", "fur", "fur","nose","dark","fur", "fur","dark","nose","fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark", T,     T,     T,     T    ],  # 12 nostrils
    [ T,     T,     T,     T,    "dark","fur", "fur",  "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark", T,     T,     T,     T    ],  # 13 below nose
    [ T,     T,     T,     T,    "dark","fur", "fur",  "fur", "fur", "fur", "fur", "fur", "fur","dark","dark","tooth","tooth","dark","dark","fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark", T,     T,     T,     T    ],  # 14 mouth + teeth
    [ T,     T,     T,     T,    "dark","fur", "fur",  "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark","dark","dark","dark","fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark", T,     T,     T,     T    ],  # 15 lower lip
    [ T,     T,     T,   "dark","fur",  "fur",  "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark", T,     T,     T,     T    ],  # 16 lower cheeks widen
    [ T,   "dark","fur",  "fur", "dark","dark","fur", "fur", "fur", "fur", "fur", "fur", "fur","dark","dark","dark","dark","fur", "fur", "fur", "fur", "fur", "fur", "fur","dark","dark", "fur", "fur", "fur","dark", T,     T    ],  # 17 chin outline + body starts
    ["dark","fur",  "fur",  "fur", "fur", "fur","dark","dark","dark","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","dark","dark","dark", "fur", "fur", "fur", "fur", "fur","dark"],  # 18 chin curves into body
    ["fur",  "fur",  "fur", "fur", "fur", "fur", "fur", "fur","dark","dark","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","dark","dark","fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur"],  # 19 chin bottom merges
    ["fur",  "fur",  "fur", "fur", "fur", "fur", "belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","fur", "fur", "fur", "fur", "fur", "fur"],  # 20 body extends past edges
    ["fur",  "fur",  "fur", "fur", "fur", "belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","fur", "fur", "fur", "fur", "fur"],  # 21 body continues off-frame
]
# fmt: on

# Regions: sets of (row, col) coordinates for pattern/intensity targeting
_FUR_PIXELS: set[tuple[int, int]] = set()
_EAR_PIXELS: set[tuple[int, int]] = set()
_NOSE_PIXELS: set[tuple[int, int]] = set()
_FOREHEAD_PIXELS: set[tuple[int, int]] = set()  # rows 0-7, inner area
_CHIN_PIXELS: set[tuple[int, int]] = set()       # rows 16-23, inner area

for _r, _row in enumerate(_FACE_TEMPLATE):
    for _c, _val in enumerate(_row):
        if _val == "ear":
            _EAR_PIXELS.add((_r, _c))
        elif _val == "fur":
            _FUR_PIXELS.add((_r, _c))
            if _r <= 7:
                _FOREHEAD_PIXELS.add((_r, _c))
            if _r >= 16:
                _CHIN_PIXELS.add((_r, _c))
        elif _val == "nose":
            _NOSE_PIXELS.add((_r, _c))

# Inner fur: fur pixels where ALL 4 neighbors are also fur/nose/eye/pupil
# (not adjacent to outline, ears, tufts, or transparency).
# Used for dalmatian spots and roan scatter to keep patterns inside the face.
_INNER_KEYS = {"fur", "nose", "eye", "pupil"}
_INNER_FUR_PIXELS: set[tuple[int, int]] = set()
for _r, _c in _FUR_PIXELS:
    _all_inner = True
    for _dr, _dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        _nr, _nc = _r + _dr, _c + _dc
        _nval = _FACE_TEMPLATE[_nr][_nc] if 0 <= _nr < len(_FACE_TEMPLATE) and 0 <= _nc < len(_FACE_TEMPLATE[0]) else None
        if _nval not in _INNER_KEYS:
            _all_inner = False
            break
    if _all_inner:
        _INNER_FUR_PIXELS.add((_r, _c))


def _seeded_rng(pig_id: str) -> _random.Random:
    """Create a deterministic RNG from a pig's UUID string."""
    seed = int(hashlib.md5(pig_id.encode()).hexdigest()[:8], 16)
    return _random.Random(seed)


def _apply_dalmatian_spots(grid: PixelGrid, pig_id: str) -> None:
    """Scatter white spots across inner fur pixels — seeded by pig ID."""
    rng = _seeded_rng(pig_id + "_dalmatian")
    fur_list = sorted(_INNER_FUR_PIXELS)  # deterministic order, interior only
    # Pick ~25-35% of inner fur pixels as spot clusters
    spot_centers = rng.sample(fur_list, k=max(1, len(fur_list) // 4))
    spotted: set[tuple[int, int]] = set()

    for r, c in spot_centers:
        spotted.add((r, c))
        # Expand each center to a small cluster (1-2 neighbors)
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if (nr, nc) in _INNER_FUR_PIXELS and rng.random() < 0.5:
                spotted.add((nr, nc))

    for r, c in spotted:
        grid[r][c] = "white"


def _apply_dutch_markings(grid: PixelGrid) -> None:
    """Apply Dutch pattern: white blaze on forehead + white chin."""
    # White blaze: center columns of forehead
    for r, c in _FOREHEAD_PIXELS:
        if 12 <= c <= 19:  # center area
            grid[r][c] = "white"

    # White chin
    for r, c in _CHIN_PIXELS:
        grid[r][c] = "white"


def _apply_himalayan(grid: PixelGrid) -> None:
    """Himalayan: lighten body fur to near-white, keep ears/nose colored."""
    for r, c in _FUR_PIXELS:
        if (r, c) not in _EAR_PIXELS:
            grid[r][c] = "belly"  # use belly (lighter) color for body


def _apply_chinchilla(grid: PixelGrid) -> None:
    """Chinchilla: silver tint — replace some inner fur with white mix."""
    for r, c in _INNER_FUR_PIXELS:
        # Alternate pixels to create a silver/ticked effect
        if (r + c) % 3 == 0:
            grid[r][c] = "white"


def _apply_roan(grid: PixelGrid, pig_id: str) -> None:
    """Roan: scatter white hairs through inner fur, seeded by pig ID."""
    rng = _seeded_rng(pig_id + "_roan")
    fur_list = sorted(_INNER_FUR_PIXELS)

    for r, c in fur_list:
        if grid[r][c] not in ("white", "eye", "pupil", "dark",  T, "tooth", T):
            if rng.random() < 0.3:  # 30% of fur pixels turn white
                grid[r][c] = "white"


def generate_portrait(
    base_color_name: str,
    pattern: str,
    intensity: str,
    roan: str,
    pig_id: str,
) -> PixelGrid:
    """Generate a 32x24 pixel face portrait from phenotype traits.

    Args:
        base_color_name: "BLACK", "CHOCOLATE", "GOLDEN", or "CREAM"
        pattern: "solid", "dutch", or "dalmatian"
        intensity: "full", "chinchilla", or "himalayan"
        roan: "none" or "roan"
        pig_id: UUID string for deterministic randomness

    Returns:
        32x24 pixel grid with palette keys. Use with convert_pixels() + PALETTES.
    """
    grid = copy.deepcopy(_FACE_TEMPLATE)

    # 1. Apply pattern (modifies fur pixels to "white")
    if pattern == "dalmatian":
        _apply_dalmatian_spots(grid, pig_id)
    elif pattern == "dutch":
        _apply_dutch_markings(grid)

    # 2. Apply intensity (lightens/modifies fur pixels)
    if intensity == "himalayan":
        _apply_himalayan(grid)
    elif intensity == "chinchilla":
        _apply_chinchilla(grid)

    # 3. Apply roan (scatters white into remaining fur)
    if roan == "roan":
        _apply_roan(grid, pig_id)

    return grid
