"""Pig sprite lookup — resolves state/direction/zoom to a pixel grid."""

from big_pig_farm.data.sprite_engine import PixelGrid, scale_pixel_grid
from big_pig_farm.data.pig_sprites import (
    PIG_PIXELS_ADULT,
    PIG_PIXELS_BABY,
    PIG_PIXELS_FAR_ADULT,
    PIG_PIXELS_FAR_BABY,
)


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
