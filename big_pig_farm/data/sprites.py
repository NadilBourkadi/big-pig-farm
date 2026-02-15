"""ASCII art definitions for guinea pigs and facilities."""

from enum import Enum
from typing import Optional

from big_pig_farm.data.sprite_engine import (
    ANIM_TICKS_PER_FRAME,
    HalfBlockRows,
    convert_pixels,
    scale_pixel_grid,
    PALETTES,
)
from big_pig_farm.data.pig_sprite_lookup import get_pig_pixel_sprite
from big_pig_farm.data.facility_pixels import (
    FACILITY_PALETTES,
    FACILITY_PIXELS,
    FACILITY_PIXELS_FAR,
)
from big_pig_farm.data.facility_pixels_close import FACILITY_PIXELS_CLOSE


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
}

# Floor texture: subtle hay/straw variation (normal + close zoom)
FLOOR_CHARS = ["·", ".", "'", ",", '"', "`", "~", ";"]
FLOOR_COLORS = ["#6e5c42", "#62553a", "#7a6850", "#685a3e", "#5e5235", "#806e55"]

# Floor texture: quieter variant for far zoom
FLOOR_CHARS_FAR = ["·", ".", "'", ","]
FLOOR_COLORS_FAR = ["#62553a", "#5e5235", "#685a3e", "#6e5c42"]

# Wall texture: warm wooden-fence colours
WALL_PLANK = ["#9B7940", "#A68550", "#8B6E35", "#B08D55", "#96753A"]
WALL_GRAIN = ["#6B4E28", "#5C4020", "#7A5A30"]
WALL_POST = "#5C3D1E"


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
    frame: int = 0,
) -> Optional[HalfBlockRows]:
    """Get a half-block rendered pig sprite with phenotype colors.

    Args:
        state: Pig display state (idle, walking, eating, sleeping, happy, sad).
        direction: LEFT or RIGHT.
        base_color: Phenotype base color name (BLACK, CHOCOLATE, GOLDEN, CREAM).
        is_baby: Whether this is a baby pig.
        zoom: Current zoom level.
        frame: Animation frame index (0 or 1). Mapped to _1/_2 suffixed keys.

    Returns:
        Half-block rows with resolved colors for all zoom levels.
    """
    close = zoom == ZoomLevel.CLOSE
    far = zoom == ZoomLevel.FAR
    pixel_grid = get_pig_pixel_sprite(state, direction.value, is_baby, close_zoom=close, far_zoom=far, frame=frame)
    palette = PALETTES.get(base_color, PALETTES["BLACK"])
    return convert_pixels(pixel_grid, palette)


def get_facility_sprite(facility_type: str, state: str = "") -> list[str]:
    """Get the sprite for a facility, optionally with a specific state."""
    if state:
        key = f"{facility_type}_{state}"
        if key in FACILITY_SPRITES:
            return FACILITY_SPRITES[key]

    return FACILITY_SPRITES.get(facility_type, ["[?]"])


def get_facility_halfblock_sprite(
    facility_type: str,
    state: str = "",
    zoom: ZoomLevel = ZoomLevel.NORMAL,
) -> Optional[HalfBlockRows]:
    """Get a half-block rendered facility sprite.

    Args:
        facility_type: Facility type value string (e.g. "food_bowl").
        state: Optional state variant ("empty", "full") for consumables.
        zoom: Current zoom level.

    Returns:
        Half-block rows with resolved colors, or None if no pixel art exists.
    """
    palette = FACILITY_PALETTES.get(facility_type)
    if palette is None:
        return None

    if zoom == ZoomLevel.FAR:
        grid = FACILITY_PIXELS_FAR.get(facility_type)
        if grid is None:
            return None
        return convert_pixels(grid, palette)

    # Normal or close zoom — look up with state variant
    if state:
        key = f"{facility_type}_{state}"
    else:
        key = facility_type

    # Close zoom: try hand-crafted sprites first, fall back to 2x scaling
    if zoom == ZoomLevel.CLOSE:
        close_grid = FACILITY_PIXELS_CLOSE.get(key)
        if close_grid is None and state:
            close_grid = FACILITY_PIXELS_CLOSE.get(facility_type)
        if close_grid is not None:
            return convert_pixels(close_grid, palette)

    grid = FACILITY_PIXELS.get(key)
    if grid is None and state:
        grid = FACILITY_PIXELS.get(facility_type)

    if grid is None:
        return None

    if zoom == ZoomLevel.CLOSE:
        grid = scale_pixel_grid(grid, 2)

    return convert_pixels(grid, palette)
