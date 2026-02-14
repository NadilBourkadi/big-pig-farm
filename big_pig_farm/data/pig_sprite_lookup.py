"""Pig sprite lookup — resolves state/direction/zoom to a pixel grid."""

from big_pig_farm.data.sprite_engine import PixelGrid, scale_pixel_grid
from big_pig_farm.data.pig_sprites import (
    PIG_PIXELS_ADULT,
    PIG_PIXELS_BABY,
    PIG_PIXELS_FAR_ADULT,
    PIG_PIXELS_FAR_BABY,
)
from big_pig_farm.data.pig_sprites_close import (
    PIG_PIXELS_CLOSE_ADULT,
    PIG_PIXELS_CLOSE_BABY,
)


def _lookup_close(key: str, direction: str, is_baby: bool) -> PixelGrid | None:
    """Try to find a hand-crafted close-zoom sprite, or return None."""
    close = PIG_PIXELS_CLOSE_BABY if is_baby else PIG_PIXELS_CLOSE_ADULT
    if key in close:
        return close[key]
    fallback = f"idle_{direction}"
    if fallback in close:
        return close[fallback]
    return None


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
    Close zoom checks hand-crafted sprites first, falls back to 2x scaling.
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
        if close_zoom:
            result = _lookup_close(anim_key, direction, is_baby)
            if result is not None:
                return result
        if anim_key in sprites:
            grid = sprites[anim_key]
            if close_zoom:
                return scale_pixel_grid(grid, 2)
            return grid

    if close_zoom:
        result = _lookup_close(key, direction, is_baby)
        if result is not None:
            return result

    if key not in sprites:
        key = f"idle_{direction}"
    grid = sprites.get(key, sprites["idle_right"])

    if close_zoom:
        return scale_pixel_grid(grid, 2)
    return grid
