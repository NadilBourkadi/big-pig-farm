"""Indicator sprite pixel data — pure data, no game logic.

Palette and pixel grid definitions for status indicator sprites shown above pigs.
Separated from indicator_sprites.py so the sprite editor can read/write this file.
"""

from big_pig_farm.data.sprite_engine import PixelGrid, T

# ---------------------------------------------------------------------------
# Color palettes — one per indicator type, with bright + dim variants
# ---------------------------------------------------------------------------

# fmt: off

INDICATOR_PALETTES: dict[str, dict[str, dict[str, str]]] = {
    "health": {
        "bright": {"a": "#ff4444", "b": "#ffffff"},
        "dim":    {"a": "#aa2222", "b": "#bb9999"},
    },
    "hunger": {
        "bright": {"a": "#dd2222", "b": "#44aa22"},
        "dim":    {"a": "#882222", "b": "#336622"},
    },
    "thirst": {
        "bright": {"a": "#4488ff", "b": "#88ccff"},
        "dim":    {"a": "#2255aa", "b": "#5588aa"},
    },
    "energy": {
        "bright": {"a": "#bb66ff", "b": "#ddaaff"},
        "dim":    {"a": "#7733aa", "b": "#9966bb"},
    },
    "pregnant": {
        "bright": {"a": "#ff66aa", "b": "#ffaacc"},
        "dim":    {"a": "#aa3366", "b": "#aa7788"},
    },
}

# --- GENERATED BELOW — do not edit above this line ---

# ---------------------------------------------------------------------------
# Normal zoom: 7w × 6h pixel grids
# ---------------------------------------------------------------------------

INDICATOR_PIXELS_NORMAL: dict[str, PixelGrid] = {
    "health": [
        [ T  ,  T  , 'a', 'a', 'a',  T  ,  T  ],
        [ T  ,  T  , 'a', 'a', 'a',  T  ,  T  ],
        ['a', 'a', 'a', 'a', 'a', 'a', 'a'],
        ['a', 'a', 'a', 'a', 'a', 'a', 'a'],
        [ T  ,  T  , 'a', 'a', 'a',  T  ,  T  ],
        [ T  ,  T  , 'a', 'a', 'a',  T  ,  T  ],
    ],
    "hunger": [
        [ T  ,  T  ,  T  , 'b', 'b',  T  ,  T  ],
        [ T  , 'a', 'a', 'b', 'a', 'a',  T  ],
        ['a', 'a', 'a', 'a', 'a', 'a', 'a'],
        ['a', 'a', 'a', 'a', 'a', 'a', 'a'],
        ['a', 'a', 'a', 'a', 'a', 'a', 'a'],
        [ T  , 'a', 'a', 'a', 'a', 'a',  T  ],
    ],
    "thirst": [
        [ T  ,  T  ,  T  , 'a',  T  ,  T  ,  T  ],
        [ T  ,  T  , 'a', 'a', 'a',  T  ,  T  ],
        [ T  , 'a', 'a', 'a', 'a', 'a',  T  ],
        [ T  , 'a', 'a', 'a', 'a', 'a',  T  ],
        [ T  , 'a', 'a', 'a', 'a', 'a',  T  ],
        [ T  ,  T  , 'a', 'a', 'a',  T  ,  T  ],
    ],
    "energy": [
        ['a', 'a', 'a', 'a', 'a', 'a', 'a'],
        [ T  ,  T  ,  T  ,  T  , 'a', 'a',  T  ],
        [ T  ,  T  ,  T  , 'a', 'a',  T  ,  T  ],
        [ T  ,  T  , 'a', 'a',  T  ,  T  ,  T  ],
        [ T  , 'a', 'a',  T  ,  T  ,  T  ,  T  ],
        ['a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ],
    "pregnant": [
        [ T  , 'a', 'a',  T  , 'a', 'a',  T  ],
        ['a', 'b', 'b', 'a', 'b', 'b', 'a'],
        ['a', 'b', 'b', 'b', 'b', 'b', 'a'],
        ['a', 'b', 'b', 'b', 'b', 'b', 'a'],
        [ T  , 'a', 'b', 'b', 'b', 'a',  T  ],
        [ T  ,  T  , 'a', 'a', 'a',  T  ,  T  ],
    ],
}


# ---------------------------------------------------------------------------
# Close zoom: 10w × 8h pixel grids (2× normal)
# ---------------------------------------------------------------------------

INDICATOR_PIXELS_CLOSE: dict[str, PixelGrid] = {
    "health": [
        [ T  ,  T  ,  T  ,  T  , 'a', 'a', 'b', 'b', 'a', 'a',  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  ,  T  ,  T  , 'a', 'a', 'b', 'b', 'a', 'a',  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  ,  T  ,  T  , 'a', 'a', 'b', 'b', 'a', 'a',  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  ,  T  ,  T  , 'a', 'a', 'b', 'b', 'a', 'a',  T  ,  T  ,  T  ,  T  ],
        ['a', 'a', 'a', 'a', 'a', 'a', 'b', 'b', 'a', 'a', 'a', 'a', 'a', 'a'],
        ['a', 'a', 'a', 'a', 'a', 'a', 'b', 'b', 'a', 'a', 'a', 'a', 'a', 'a'],
        ['a', 'a', 'a', 'a', 'a', 'a', 'b', 'b', 'a', 'a', 'a', 'a', 'a', 'a'],
        ['a', 'a', 'a', 'a', 'a', 'a', 'b', 'b', 'a', 'a', 'a', 'a', 'a', 'a'],
        [ T  ,  T  ,  T  ,  T  , 'a', 'a', 'b', 'b', 'a', 'a',  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  ,  T  ,  T  , 'a', 'a', 'b', 'b', 'a', 'a',  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  ,  T  ,  T  , 'a', 'a', 'b', 'b', 'a', 'a',  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  ,  T  ,  T  , 'a', 'a', 'b', 'b', 'a', 'a',  T  ,  T  ,  T  ,  T  ],
    ],
    "hunger": [
        [ T  ,  T  ,  T  ,  T  ,  T  ,  T  , 'b', 'b', 'b', 'b',  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  ,  T  ,  T  ,  T  ,  T  , 'b', 'b', 'b', 'b',  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  , 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a',  T  ,  T  ],
        [ T  ,  T  , 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a',  T  ,  T  ],
        ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
        ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
        ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
        ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
        ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
        ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
        [ T  ,  T  ,  T  ,  T  , 'a', 'a', 'a', 'a', 'a', 'a',  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  ,  T  ,  T  , 'a', 'a', 'a', 'a', 'a', 'a',  T  ,  T  ,  T  ,  T  ],
    ],
    "thirst": [
        [ T  ,  T  ,  T  ,  T  ,  T  ,  T  , 'b', 'b',  T  ,  T  ,  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  ,  T  ,  T  ,  T  ,  T  , 'b', 'b',  T  ,  T  ,  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  ,  T  ,  T  , 'a', 'a', 'b', 'b', 'a', 'a',  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  ,  T  ,  T  , 'a', 'a', 'b', 'b', 'a', 'a',  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  , 'a', 'a', 'a', 'a', 'b', 'b', 'a', 'a', 'a', 'a',  T  ,  T  ],
        [ T  ,  T  , 'a', 'a', 'a', 'a', 'b', 'b', 'a', 'a', 'a', 'a',  T  ,  T  ],
        ['a', 'a', 'a', 'a', 'a', 'a', 'b', 'b', 'a', 'a', 'a', 'a', 'a', 'a'],
        ['a', 'a', 'a', 'a', 'a', 'a', 'b', 'b', 'a', 'a', 'a', 'a', 'a', 'a'],
        ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
        ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
        [ T  ,  T  , 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a',  T  ,  T  ],
        [ T  ,  T  , 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a',  T  ,  T  ],
    ],
    "energy": [
        ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
        ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
        [ T  ,  T  ,  T  ,  T  ,  T  ,  T  ,  T  ,  T  , 'a', 'a', 'a', 'a',  T  ,  T  ],
        [ T  ,  T  ,  T  ,  T  ,  T  ,  T  ,  T  ,  T  , 'a', 'a', 'a', 'a',  T  ,  T  ],
        [ T  ,  T  ,  T  ,  T  ,  T  ,  T  , 'a', 'a', 'a', 'a',  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  ,  T  ,  T  ,  T  ,  T  , 'a', 'a', 'a', 'a',  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  ,  T  ,  T  , 'a', 'a', 'a', 'a',  T  ,  T  ,  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  ,  T  ,  T  , 'a', 'a', 'a', 'a',  T  ,  T  ,  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  , 'a', 'a', 'a', 'a',  T  ,  T  ,  T  ,  T  ,  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  , 'a', 'a', 'a', 'a',  T  ,  T  ,  T  ,  T  ,  T  ,  T  ,  T  ,  T  ],
        ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
        ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
    ],
    "pregnant": [
        [ T  ,  T  , 'a', 'a', 'a', 'a',  T  ,  T  , 'a', 'a', 'a', 'a',  T  ,  T  ],
        [ T  ,  T  , 'a', 'a', 'a', 'a',  T  ,  T  , 'a', 'a', 'a', 'a',  T  ,  T  ],
        ['a', 'a', 'b', 'b', 'b', 'b', 'a', 'a', 'b', 'b', 'b', 'b', 'a', 'a'],
        ['a', 'a', 'b', 'b', 'b', 'b', 'a', 'a', 'b', 'b', 'b', 'b', 'a', 'a'],
        ['a', 'a', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'a', 'a'],
        ['a', 'a', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'a', 'a'],
        ['a', 'a', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'a', 'a'],
        ['a', 'a', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'a', 'a'],
        [ T  ,  T  , 'a', 'a', 'b', 'b', 'b', 'b', 'b', 'b', 'a', 'a',  T  ,  T  ],
        [ T  ,  T  , 'a', 'a', 'b', 'b', 'b', 'b', 'b', 'b', 'a', 'a',  T  ,  T  ],
        [ T  ,  T  ,  T  ,  T  , 'a', 'a', 'a', 'a', 'a', 'a',  T  ,  T  ,  T  ,  T  ],
        [ T  ,  T  ,  T  ,  T  , 'a', 'a', 'a', 'a', 'a', 'a',  T  ,  T  ,  T  ,  T  ],
    ],
}

# fmt: on
