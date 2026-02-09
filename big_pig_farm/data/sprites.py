"""ASCII art definitions for guinea pigs and facilities."""

from enum import Enum
from typing import Optional

from big_pig_farm.data.sprite_pixels import (
    HalfBlockRows,
    convert_pixels,
    get_pig_pixel_sprite,
    PALETTES,
)


class ZoomLevel(Enum):
    """Farm viewport zoom levels."""
    FAR = "far"
    NORMAL = "normal"
    CLOSE = "close"


ZOOM_SCALES: dict[ZoomLevel, float] = {
    ZoomLevel.FAR: 0.5,
    ZoomLevel.NORMAL: 1.0,
    ZoomLevel.CLOSE: 2.0,
}


class Direction(Enum):
    """Facing direction for sprites."""
    LEFT = "left"
    RIGHT = "right"


# Guinea pig sprites - standard size (5 wide x 4 tall)
PIG_SPRITES = {
    "idle_right": [
        "  .--. ",
        " ( o.o)",
        " |>  <|",
        "  '--' ",
    ],
    "idle_left": [
        " .--.  ",
        "(o.o ) ",
        "|>  <| ",
        " '--'  ",
    ],
    "walking_right": [
        "  .--. ",
        " ( o.o)",
        " />  <\\",
        "  '--' ",
    ],
    "walking_left": [
        " .--.  ",
        "(o.o ) ",
        "/>  <\\ ",
        " '--'  ",
    ],
    "eating_right": [
        "  .--. ",
        " ( ^.^)",
        " |> @<|",
        "  '--' ",
    ],
    "eating_left": [
        " .--.  ",
        "(^.^ ) ",
        "|>@ <| ",
        " '--'  ",
    ],
    "sleeping_right": [
        "  .--. ",
        " ( -.-)",
        " |>  <| zzZ",
        "  '--' ",
    ],
    "sleeping_left": [
        " .--.  ",
        "(-.- ) ",
        "zzZ |>  <|",
        " '--'  ",
    ],
    "happy_right": [
        "  .--. ",
        " ( ^o^)",
        " |>  <|",
        "  '--' ",
    ],
    "happy_left": [
        " .--.  ",
        "(^o^ ) ",
        "|>  <| ",
        " '--'  ",
    ],
    "sad_right": [
        "  .--. ",
        " ( ;.;)",
        " |>  <|",
        "  '--' ",
    ],
    "sad_left": [
        " .--.  ",
        "(;.; ) ",
        "|>  <| ",
        " '--'  ",
    ],
}

# Baby guinea pig sprites (3 wide x 2 tall)
BABY_PIG_SPRITES = {
    "idle_right": [
        " (o.o)",
        " |><| ",
    ],
    "idle_left": [
        "(o.o) ",
        " |><| ",
    ],
    "walking_right": [
        " (o.o)",
        " /><\\ ",
    ],
    "walking_left": [
        "(o.o) ",
        "/><\\ ",
    ],
    "sleeping_right": [
        " (-.-) z",
        " |><|  ",
    ],
    "sleeping_left": [
        "z (-.-)",
        "  |><| ",
    ],
}

# Facility sprites
FACILITY_SPRITES = {
    "food_bowl": [
        "┌─BOWL─┐",
        "│●●●●○○│",
        "└──────┘",
    ],
    "food_bowl_empty": [
        "┌─BOWL─┐",
        "│○○○○○○│",
        "└──────┘",
    ],
    "food_bowl_full": [
        "┌─BOWL─┐",
        "│●●●●●●│",
        "└──────┘",
    ],
    "water_bottle": [
        "╭───╮",
        "│~~~│",
        "│   │",
        "╰─┬─╯",
        "  ○  ",
    ],
    "water_bottle_empty": [
        "╭───╮",
        "│   │",
        "│   │",
        "╰─┬─╯",
        "  ○  ",
    ],
    "hay_rack": [
        "┌─HAY─┐",
        "│░░░░░│",
        "└─────┘",
    ],
    "hay_rack_empty": [
        "┌─HAY─┐",
        "│     │",
        "└─────┘",
    ],
    "hideout": [
        "┌SHELTER─┐",
        "│▓▓▓▓▓▓▓▓│",
        "└────────┘",
    ],
    "exercise_wheel": [
        "┌─WHEEL─┐",
        "│  ◯    │",
        "└───────┘",
    ],
    "tunnel": [
        "═══════",
        "       ",
        "═══════",
    ],
    "play_area": [
        "┌─PLAY──┐",
        "│ ♦ ○ ● │",
        "│  ▲ ■  │",
        "└───────┘",
    ],
    "breeding_den": [
        "╭─LOVE─╮",
        "│ ♥  ♥ │",
        "╰──────╯",
    ],
    "nursery": [
        "┌NURSERY─┐",
        "│ ☆  ☆  │",
        "│  ★    │",
        "└────────┘",
    ],
    "veggie_garden": [
        "┌GARDEN─┐",
        "│♣♣♣♣♣♣│",
        "│♣♣♣♣♣♣│",
        "└───────┘",
    ],
    "grooming_station": [
        "┌GROOM┐",
        "│  ✂  │",
        "└─────┘",
    ],
    "genetics_lab": [
        "┌─G.LAB──┐",
        "│ ⚗ DNA ⚗│",
        "│ ◊  ◊  ◊│",
        "└─────────┘",
    ],
}

# Far-zoom facility icons — compact distinguishable per-type icons
FAR_FACILITY_SPRITES: dict[str, str] = {
    "food_bowl": "(●)",
    "water_bottle": "╤",
    "hay_rack": "░░",
    "hideout": "┌─┐",
    "exercise_wheel": "(◯)",
    "tunnel": "═══",
    "play_area": "♦○●",
    "breeding_den": "♥",
    "nursery": "☆",
    "veggie_garden": "♣♣",
    "grooming_station": "✂",
    "genetics_lab": "⚗",
}

# Terrain characters
TERRAIN = {
    "floor": "·",
    "bedding": "░",
    "grass": "♣",
    "wall_h": "─",
    "wall_v": "│",
    "corner_tl": "┌",
    "corner_tr": "┐",
    "corner_bl": "└",
    "corner_br": "┘",
}


def get_pig_sprite(state: str, direction: Direction, is_baby: bool = False) -> list[str]:
    """Get the appropriate sprite for a guinea pig's current state and direction."""
    sprites = BABY_PIG_SPRITES if is_baby else PIG_SPRITES
    key = f"{state}_{direction.value}"

    if key in sprites:
        return sprites[key]

    # Fallback to idle
    fallback = f"idle_{direction.value}"
    return sprites.get(fallback, sprites["idle_right"])


def get_pig_halfblock_sprite(
    state: str,
    direction: Direction,
    base_color: str,
    is_baby: bool = False,
    zoom: ZoomLevel = ZoomLevel.NORMAL,
) -> Optional[HalfBlockRows]:
    """Get a half-block rendered pig sprite with phenotype colors.

    Args:
        state: Pig display state (idle, walking, eating, sleeping, happy, sad).
        direction: LEFT or RIGHT.
        base_color: Phenotype base color name (BLACK, CHOCOLATE, GOLDEN, CREAM).
        is_baby: Whether this is a baby pig.
        zoom: Current zoom level.

    Returns:
        Half-block rows with resolved colors for all zoom levels.
    """
    close = zoom == ZoomLevel.CLOSE
    far = zoom == ZoomLevel.FAR
    pixel_grid = get_pig_pixel_sprite(state, direction.value, is_baby, close_zoom=close, far_zoom=far)
    palette = PALETTES.get(base_color, PALETTES["BLACK"])
    return convert_pixels(pixel_grid, palette)


def get_facility_sprite(facility_type: str, state: str = "") -> list[str]:
    """Get the sprite for a facility, optionally with a specific state."""
    if state:
        key = f"{facility_type}_{state}"
        if key in FACILITY_SPRITES:
            return FACILITY_SPRITES[key]

    return FACILITY_SPRITES.get(facility_type, ["[?]"])
