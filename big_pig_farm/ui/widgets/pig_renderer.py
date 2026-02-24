"""Guinea pig rendering functions for the farm view.

Module-level functions that draw pigs (sprites, names, status indicators)
into FarmView's character/style buffers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.style import Style

from big_pig_farm.data.indicator_sprites import (
    IndicatorType,
    get_far_indicator,
    get_indicator_halfblock,
    get_pig_indicator_type,
)
from big_pig_farm.data.sprites import (
    ANIM_FRAME_COUNT,
    ANIM_TICKS_PER_FRAME,
    Direction,
    ZoomLevel,
    get_pig_halfblock_sprite,
)
from big_pig_farm.entities.guinea_pig import GuineaPig

if TYPE_CHECKING:
    from big_pig_farm.ui.widgets.farm_view import FarmView

# Indicator timing (in render ticks, ~15fps)
_INDICATOR_SHOW_TICKS = 45       # ~3 seconds visible
_INDICATOR_COOLDOWN_TICKS = 150  # ~10 seconds hidden
_INDICATOR_PULSE_TICKS = 8       # toggle bright/dim every ~0.5s


class _IndicatorTimer:
    """Tracks the ephemeral show/cooldown cycle for one pig's status indicator."""
    __slots__ = ("indicator_type", "trigger_tick", "visible")

    def __init__(self, indicator_type: IndicatorType, trigger_tick: int) -> None:
        self.indicator_type = indicator_type
        self.trigger_tick = trigger_tick
        self.visible = True


def draw_guinea_pigs(
    view: FarmView,
    width: int,
    height: int,
    offset_x: int,
    offset_y: int,
) -> None:
    """Draw all guinea pigs, sorted by Y so lower pigs draw on top."""
    pigs = sorted(view.state.get_pigs_list(), key=lambda p: p.position.y)
    for pig in pigs:
        draw_pig(view, pig, width, height, offset_x, offset_y)


def draw_pig(
    view: FarmView,
    pig: GuineaPig,
    width: int,
    height: int,
    offset_x: int,
    offset_y: int,
) -> None:
    """Draw a single guinea pig using half-block sprites (or dot at far zoom)."""
    scale = view._scale()

    # Determine direction -- look ahead in path for meaningful horizontal
    # movement.  Only update the stored facing when a clear direction is
    # found, so vertical movement and float-boundary crossings don't cause
    # rapid left/right flipping.
    if pig.path and len(pig.path) > 0:
        for wx, _wy in pig.path:
            if wx > pig.position.x + 0.5:
                view._pig_facing[pig.id] = Direction.RIGHT
                break
            elif wx < pig.position.x - 0.5:
                view._pig_facing[pig.id] = Direction.LEFT
                break
    direction = view._pig_facing.get(pig.id, Direction.RIGHT)

    is_selected = pig.id == view.selected_pig_id

    # Screen position of the pig's world coordinate
    base_x = int((pig.position.x - view._viewport_x) * scale) + offset_x
    base_y = int((pig.position.y - view._viewport_y) * scale) + offset_y

    base_color_name = pig.phenotype.base_color.name  # BLACK, CHOCOLATE, etc.

    # --- All zoom levels: half-block sprite ---
    tpf = ANIM_TICKS_PER_FRAME.get(pig.display_state)
    if tpf:
        pig_hash = pig.id.int
        speed_var = (pig_hash >> 8) % 3 - 1   # -1, 0, or +1
        tpf = max(2, tpf + speed_var)
        frame_count = ANIM_FRAME_COUNT.get(pig.display_state, 2)
        # Ping-pong: 3 frames -> 0,1,2,1,0,1,2,1 ... (cycle_len=4)
        cycle_len = (frame_count - 1) * 2 if frame_count > 1 else 1
        phase = pig_hash % (tpf * cycle_len)
        pos = ((view._render_tick + phase) // tpf) % cycle_len
        frame = pos if pos < frame_count else cycle_len - pos
    else:
        frame = 0

    halfblock = get_pig_halfblock_sprite(
        pig.display_state, direction, base_color_name,
        is_baby=pig.is_baby, zoom=view._zoom, frame=frame,
    )
    if halfblock is None:
        return

    sprite_h = len(halfblock)
    sprite_w = len(halfblock[0]) if halfblock else 0

    # Center sprite on pig position
    anchor_x = base_x - sprite_w // 2
    anchor_y = base_y - sprite_h // 2

    # Draw oval glow under selected pig (before sprite so it shows
    # through transparent/edge pixels)
    if is_selected and view._zoom != ZoomLevel.FAR:
        glow_bg = "#8a7010"
        pad = 2  # padding around sprite for ellipse bounds
        cx = anchor_x + (sprite_w - 1) / 2
        cy = anchor_y + (sprite_h - 1) / 2
        rx = (sprite_w + 2 * pad) / 2
        ry = (sprite_h + 2 * pad) / 2
        for gy in range(anchor_y - pad, anchor_y + sprite_h + pad):
            for gx in range(anchor_x - pad, anchor_x + sprite_w + pad):
                if ((gx - cx) / rx) ** 2 + ((gy - cy) / ry) ** 2 > 1.0:
                    continue
                if 0 <= gx < width and 0 <= gy < height:
                    existing = view._style_buffer[gy][gx]
                    fg = existing.color if existing else None
                    glow_style = Style(color=fg, bgcolor=glow_bg)
                    view._style_buffer[gy][gx] = glow_style
                    view._terrain_bg_buffer[gy][gx] = glow_style

    # Draw half-block sprite (always use natural colors)
    for dy, row in enumerate(halfblock):
        for dx, (char, fg, bg) in enumerate(row):
            screen_x = anchor_x + dx
            screen_y = anchor_y + dy

            if not (0 <= screen_x < width and 0 <= screen_y < height):
                continue

            if char == " " and fg is None and bg is None:
                continue  # Transparent pixel -- don't overwrite background

            # For semi-transparent edge cells, inherit the bg from
            # the terrain/facility layer so the pig blends with the
            # ground instead of picking up another pig's body color.
            effective_bg = bg
            if effective_bg is None:
                terrain = view._terrain_bg_buffer[screen_y][screen_x]
                if terrain is not None:
                    effective_bg = terrain.bgcolor

            style = Style(color=fg, bgcolor=effective_bg)

            view._char_buffer[screen_y][screen_x] = char
            view._style_buffer[screen_y][screen_x] = style

    # Draw status indicator above pig (skip for selected pig -- sidebar shows details)
    if not is_selected:
        _draw_indicator(view, pig, width, height, anchor_x, anchor_y, base_x, sprite_w)

    # Draw name below pig (skip at far zoom -- no room)
    if view._zoom != ZoomLevel.FAR:
        name_y = anchor_y + sprite_h
        if 0 <= name_y < height:
            name = pig.name[:10]
            name_x = base_x - len(name) // 2
            name_style = (
                Style(color="bright_yellow", bold=True) if is_selected
                else Style(color="white", dim=True)
            )
            for i, char in enumerate(name):
                if 0 <= name_x + i < width:
                    view._char_buffer[name_y][name_x + i] = char
                    view._style_buffer[name_y][name_x + i] = name_style


# ------------------------------------------------------------------
# Status indicators
# ------------------------------------------------------------------


def _update_indicator_timer(
    view: FarmView, pig: GuineaPig,
) -> IndicatorType | None:
    """Manage the show/cooldown/resurface cycle for a pig's status indicator.

    Returns the IndicatorType to draw, or None if nothing should be shown.
    """
    current_type = get_pig_indicator_type(pig)
    timer = view._indicator_timers.get(pig.id)
    tick = view._render_tick

    # No critical need -- clear timer entirely
    if current_type is None:
        view._indicator_timers.pop(pig.id, None)
        return None

    # New indicator or type changed -- start fresh
    if timer is None or timer.indicator_type != current_type:
        timer = _IndicatorTimer(current_type, tick)
        view._indicator_timers[pig.id] = timer
        return current_type

    elapsed = tick - timer.trigger_tick

    # Show phase
    if elapsed < _INDICATOR_SHOW_TICKS:
        return current_type

    # Cooldown phase
    if elapsed < _INDICATOR_SHOW_TICKS + _INDICATOR_COOLDOWN_TICKS:
        return None

    # Cooldown expired -- resurface
    timer.trigger_tick = tick
    return current_type


def _draw_indicator(
    view: FarmView,
    pig: GuineaPig,
    width: int,
    height: int,
    anchor_x: int,
    anchor_y: int,
    base_x: int,
    sprite_w: int,
) -> None:
    """Draw a floating status indicator icon above a pig."""
    indicator_type = _update_indicator_timer(view, pig)
    if indicator_type is None:
        return

    # Pulse animation: toggle bright/dim
    bright = (view._render_tick // _INDICATOR_PULSE_TICKS) % 2 == 0

    zoom_val = view._zoom.value  # "far", "normal", "close"

    if view._zoom == ZoomLevel.FAR:
        char, color = get_far_indicator(indicator_type, bright)
        icon_x = base_x
        icon_y = anchor_y - 1
        if 0 <= icon_x < width and 0 <= icon_y < height:
            view._char_buffer[icon_y][icon_x] = char
            view._style_buffer[icon_y][icon_x] = Style(color=color)
        return

    halfblock = get_indicator_halfblock(indicator_type, zoom_val, bright)
    if halfblock is None:
        return

    icon_h = len(halfblock)
    icon_w = len(halfblock[0]) if halfblock else 0

    # Position: centered horizontally on pig, directly above sprite top
    icon_x = base_x - icon_w // 2
    icon_y = anchor_y - icon_h

    for dy, row in enumerate(halfblock):
        for dx, (char, fg, bg) in enumerate(row):
            sx = icon_x + dx
            sy = icon_y + dy
            if not (0 <= sx < width and 0 <= sy < height):
                continue
            if char == " " and fg is None and bg is None:
                continue
            view._char_buffer[sy][sx] = char
            view._style_buffer[sy][sx] = Style(color=fg, bgcolor=bg)


def pig_at_screen_pos(
    view: FarmView, screen_x: int, screen_y: int,
) -> GuineaPig | None:
    """Return the pig whose sprite covers (screen_x, screen_y), or None."""
    scale = view._scale()
    width = view.size.width
    height = view.size.height

    farm = view.state.farm
    scaled_w = int(farm.width * scale)
    scaled_h = int(farm.height * scale)
    offset_x = max(0, (width - scaled_w) // 2)
    offset_y = max(0, (height - scaled_h) // 2)

    best_pig: GuineaPig | None = None
    best_dist = float("inf")

    for pig in view.state.get_pigs_list():
        direction = view._pig_facing.get(pig.id, Direction.RIGHT)
        base_color_name = pig.phenotype.base_color.name

        # Use frame=0 for hit-testing -- all frames share the same dimensions
        halfblock = get_pig_halfblock_sprite(
            pig.display_state, direction, base_color_name,
            is_baby=pig.is_baby, zoom=view._zoom, frame=0,
        )
        if halfblock is None:
            continue

        sprite_h = len(halfblock)
        sprite_w = len(halfblock[0])

        base_x = int((pig.position.x - view._viewport_x) * scale) + offset_x
        base_y = int((pig.position.y - view._viewport_y) * scale) + offset_y

        anchor_x = base_x - sprite_w // 2
        anchor_y = base_y - sprite_h // 2

        # 1px padding on small sprites so far-zoom dots are easier to click
        pad = 1 if sprite_w <= 3 or sprite_h <= 3 else 0
        if not (anchor_x - pad <= screen_x < anchor_x + sprite_w + pad
                and anchor_y - pad <= screen_y < anchor_y + sprite_h + pad):
            continue

        # Pick the pig closest to the click point (overlapping pigs
        # resolve by center distance, not render Z-order)
        dist = abs(screen_x - base_x) + abs(screen_y - base_y)
        if dist < best_dist:
            best_dist = dist
            best_pig = pig

    return best_pig
