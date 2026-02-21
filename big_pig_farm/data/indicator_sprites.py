"""Status indicator sprites — floating icons above pigs for critical needs.

Small half-block icons that pop up above a pig when a need becomes critical.
Each zoom level has its own visual representation.
"""

from enum import Enum
from typing import Optional

from big_pig_farm.data.sprite_engine import HalfBlockRows, convert_pixels
from big_pig_farm.data.config import NEEDS
from big_pig_farm.data.indicator_pixels import (
    INDICATOR_PALETTES,
    INDICATOR_PIXELS_CLOSE,
    INDICATOR_PIXELS_NORMAL,
)
from big_pig_farm.entities.guinea_pig import BehaviorState, GuineaPig


class IndicatorType(Enum):
    """Status indicator types, ordered by display priority."""
    HEALTH = "health"
    HUNGER = "hunger"
    THIRST = "thirst"
    ENERGY = "energy"
    COURTING = "courting"
    PREGNANT = "pregnant"


# --- Thresholds ---
_LOW = NEEDS.LOW_THRESHOLD  # 40 — show indicator when need drops below this


# --- FAR zoom: single character + color ---

FAR_INDICATORS: dict[IndicatorType, dict[str, tuple[str, str]]] = {
    IndicatorType.HEALTH:   {"bright": ("+", "#ff4444"), "dim": ("+", "#aa2222")},
    IndicatorType.HUNGER:   {"bright": ("!", "#dd2222"), "dim": ("!", "#882222")},
    IndicatorType.THIRST:   {"bright": ("~", "#4488ff"), "dim": ("~", "#2255aa")},
    IndicatorType.ENERGY:   {"bright": ("z", "#bb66ff"), "dim": ("z", "#7733aa")},
    IndicatorType.COURTING: {"bright": ("♥", "#ff4488"), "dim": ("♥", "#cc2266")},
    IndicatorType.PREGNANT: {"bright": ("♥", "#ff66aa"), "dim": ("♥", "#aa3366")},
}


def get_pig_indicator_type(pig: GuineaPig) -> Optional[IndicatorType]:
    """Check pig needs in priority order, return highest-priority active indicator.

    An indicator shows when the need drops below LOW_THRESHOLD *or* when the
    pig has decided to address that need (is actively eating/drinking/sleeping).
    """
    if pig.needs.health < _LOW:
        return IndicatorType.HEALTH
    if pig.needs.hunger < _LOW or pig.behavior_state == BehaviorState.EATING:
        return IndicatorType.HUNGER
    if pig.needs.thirst < _LOW or pig.behavior_state == BehaviorState.DRINKING:
        return IndicatorType.THIRST
    if pig.needs.energy < _LOW or pig.behavior_state == BehaviorState.SLEEPING:
        return IndicatorType.ENERGY
    if pig.behavior_state == BehaviorState.COURTING:
        return IndicatorType.COURTING
    if pig.is_pregnant:
        return IndicatorType.PREGNANT
    return None


def get_indicator_halfblock(
    indicator_type: IndicatorType,
    zoom: str,
    bright: bool = True,
) -> Optional[HalfBlockRows]:
    """Return half-block rows for an indicator sprite at the given zoom level.

    Args:
        indicator_type: Which indicator to render.
        zoom: ZoomLevel value string ("far", "normal", "close").
        bright: True for bright pulse frame, False for dim.

    Returns:
        HalfBlockRows for NORMAL/CLOSE zoom, or None for FAR (use get_far_indicator).
    """
    name = indicator_type.value
    phase = "bright" if bright else "dim"
    palette = INDICATOR_PALETTES[name][phase]

    if zoom == "normal":
        pixels = INDICATOR_PIXELS_NORMAL[name]
    elif zoom == "close":
        pixels = INDICATOR_PIXELS_CLOSE[name]
    else:
        return None

    return convert_pixels(pixels, palette)


def get_far_indicator(
    indicator_type: IndicatorType,
    bright: bool = True,
) -> tuple[str, str]:
    """Return (character, color) for a FAR-zoom indicator.

    Args:
        indicator_type: Which indicator to render.
        bright: True for bright pulse frame, False for dim.

    Returns:
        Tuple of (character, Rich color string).
    """
    phase = "bright" if bright else "dim"
    return FAR_INDICATORS[indicator_type][phase]
