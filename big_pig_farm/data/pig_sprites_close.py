"""Hand-crafted close-zoom pig pixel sprites (28w×16h adult, 16w×12h baby).

Only right-facing variants are drawn here; left-facing ones are auto-generated
by mirroring each row.  Uses compact single-char encoding decoded at import time.

The silhouette (transparent vs non-transparent boundary) matches the 2x-scaled
normal sprites exactly — this guarantees smooth outlines.  Interior pixels are
refined to break up the 2x2 blockiness: ears, eyes, nose, and belly transitions
differ between paired rows.
"""

from big_pig_farm.data.sprite_engine import (
    PixelGrid,
    build_mirrored_dict,
    decode_sprite,
)

# Character maps — one char per palette key
_PIG_CHAR = {
    ".": None, "d": "dark", "f": "fur", "s": "shade", "b": "belly",
    "e": "eye", "p": "pupil", "n": "nose", "a": "ear", "w": "paw",
}

# fmt: off

# ---------------------------------------------------------------------------
# Adult close-zoom sprites (28w × 16h)
#
# Silhouette matches scale_pixel_grid(normal, 2) exactly.
# Interior detail refined: each row pair is unpaired for less blockiness.
# ---------------------------------------------------------------------------

_CLOSE_IDLE_R: PixelGrid = decode_sprite([
    "................ddddaadd",
    "....ddddddddddddddfaafddd",
    "...ddssssssssffdffffffffdd",
    "..ddsffffffffffffffsssssddd",
    ".ddsffffffffffffffseeeppsfdd",
    "ddfffffffffffffffseeepppsffd",
    "dffffffffffffffffseeppppsnnd",
    "dfffffffffffffffffsepppsfnnd",
    "dffffffffffffffffffssssfffdd",
    ".dffffffffffffffffffffffffd",
    "..ddsffffffffffffffffffffdd",
    "...dsffffffffffffffffffddd",
    "...dddsffssssssssssfffdd",
    ".....dsfddddddddddddsfd",
    ".....dsfd..........dsfd",
    "......dd............dd",
], _PIG_CHAR, width=28)

_CLOSE_WALKING_R_1: PixelGrid = decode_sprite([
    "................ddddaadd",
    "....ddddddddddddddfaafddd",
    "...ddssssssssffdffffffffdd",
    "..ddsffffffffffffffsssssddd",
    ".ddsffffffffffffffseeeppsfdd",
    "ddfffffffffffffffseeepppsffd",
    "dffffffffffffffffseeppppsnnd",
    "dfffffffffffffffffsepppsfnnd",
    "dffffffffffffffffffssssfffdd",
    ".dffffffffffffffffffffffffd",
    "..ddsffffffffffffffffffffdd",
    "...dsfffffsssssssffffffddd",
    "...dssssffdddddddssfffdd",
    ".....ddsffddddddddddsfd",
    "......dsffd........dsfd",
    "......ddddd........dddd",
], _PIG_CHAR, width=28)

_CLOSE_EATING_R_1: PixelGrid = decode_sprite([
    "................ddddaadd",
    "....ddddddddddddddfaafddd",
    "...ddssssssssssdffffffffdd",
    "..ddsffffffffffffffssssfddd",
    ".ddsffffffffffffffsppppsffdd",
    "ddffffffffffffffffppppppfffd",
    "dfffffffffffffffffpsssspfnnd",
    "dffffffffffffffffffffffffnnd",
    "dffffffffffffffffffffffpeedd",
    ".dffffffffffffffffffffppppd",
    "..ddsffffffffffffffffffppdd",
    "...dsffffffffffffffffffddd",
    "...dddsffssssssssssfffdd",
    ".....dsfddddddddddddsfd",
    ".....dsfd..........dsfd",
    "......dd............dd",
], _PIG_CHAR, width=28)

_CLOSE_SLEEPING_R_1: PixelGrid = decode_sprite([
    "................ddddaadd",
    "...............dddfaafddd",
    "......ddddddddddffffffffdd",
    ".....dddddfffffdffffffffddd",
    "....ddddffffffffffddddffffdd",
    "...dddddfffffffffffdddffffdd",
    "..ddffffffffffffffffffffnndd",
    ".dddffffffffffffffffffffnndd",
    "ddffffffffffffffffffffffffdd",
    ".dffffffffffffffffffffffffd",
    "..ddbbffffffffffffffffbbdd",
    "...dbffffffffffffffffffbd",
    "....ddbbbbbbbbbbbbbbbbdd",
    "....ddbbbbbbbbbbbbbbbbdd",
    ".....dwf............fwd",
    ".....dww............wwd",
], _PIG_CHAR, width=28)

_CLOSE_HAPPY_R_1: PixelGrid = decode_sprite([
    "................ddddaadd",
    "....ddddddddddddddfaafddd",
    "...ddssssssssssdffffffffdd",
    "..ddsffffffffffffffssssfddd",
    ".ddsffffffffffffffsppppsffdd",
    "ddffffffffffffffffppppppfffd",
    "dfffffffffffffffffpsssspfnnd",
    "dffffffffffffffffffffffffnnd",
    "dfffffffffffffffffffffffffdd",
    ".dfffffffffffffffffffff...d",
    "..ddsffffffffffffffffff..dd",
    "...dsfffffffffffffffffffdd",
    "...dddsffssssssssssfffdd",
    ".....dsfddddddddddddsfd",
    ".....dsfd..........dsfd",
    "......dd............dd",
], _PIG_CHAR, width=28)

_CLOSE_SAD_R: PixelGrid = decode_sprite([
    "................ddddaadd",
    "...............dddfaafddd",
    "......ddddddddddffffffffdd",
    ".....dddddfffffdffffffffddd",
    "....ddddffffffffffeeeeppffdd",
    "...dddddffffffffffeeepppffdd",
    "..ddffffffffffffffeeppppnndd",
    ".dddffffffffffffffeepppfnndd",
    "ddffffffffffffffffffffffffdd",
    ".dffffffffffffffffffffffffd",
    "..ddbbffffffffffffffffbbdd",
    "...dbffffffffffffffffffbd",
    "....ddbbbbbbbbbbbbbbbbdd",
    "....ddbbbbbbbbbbbbbbbbdd",
    ".....dwf............fwd",
    ".....dww............wwd",
], _PIG_CHAR, width=28)

_CLOSE_WALKING_R_2: PixelGrid = decode_sprite([
    "",
    "",
    "................ddddaadd",
    "....ddddddddddddddfaafddd",
    "...ddssssssssffdffffffffdd",
    "..ddsffffffffffffffsssssddd",
    ".ddsffffffffffffffseeeppsfdd",
    "ddfffffffffffffffseeepppsffd",
    "dffffffffffffffffseeppppsnnd",
    "dfffffffffffffffffsepppsfnnd",
    "dffffffffffffffffffssssfffdd",
    ".dffffffffffffffffffffffffd",
    "..ddsffffffssssssffffffffdd",
    "...dsssssssssssssssssssddd",
    "...ddsssssddddddddssssdd",
    "....ddddddd......dddddd",
], _PIG_CHAR, width=28)

_CLOSE_WALKING_R_3: PixelGrid = decode_sprite([
    "................ddddaadd",
    "....ddddddddddddddfaafddd",
    "...ddssssssssffdffffffffdd",
    "..ddsffffffffffffffsssssddd",
    ".ddsffffffffffffffseeeppsfdd",
    "ddfffffffffffffffseeepppsffd",
    "dffffffffffffffffseeppppsnnd",
    "dfffffffffffffffffsepppsfnnd",
    "dffffffffffffffffffssssfffdd",
    ".dffffffffffffffffffffffffd",
    "..ddsffffffffffffffffffffdd",
    "...dsfffffsssssssffffffddd",
    "...dsffffsdddddddssffffd",
    "...dsfffddddddddddsfffd",
    "...dsfffd........dsffdd",
    "...ddddd.........ddddd",
], _PIG_CHAR, width=28)

_CLOSE_EATING_R_2: PixelGrid = decode_sprite([
    "................ddddaadd",
    "....ddddddddddddddfaafddd",
    "...ddssssssssssdffffffffdd",
    "..ddssfffffffffffffssssfddd",
    ".ddssfffffffffffffsppppsffdd",
    "ddsfffffffffffffffppppppfffd",
    "dsffffffffffffffffpsssspfnnd",
    "dffffffffffffffffffffffffnnd",
    "dfffffffffffffffffffffffffdd",
    ".dffffffffffffffffffffppeed",
    "..ddsffffffffffffffffffppdd",
    "...dssfffffffffssssfffffdd",
    "...dddsffsssssssssssffdd",
    ".....dsfddddddddddddsfd",
    ".....dsfd..........dsfd",
    "......dd............dd",
], _PIG_CHAR, width=28)

_CLOSE_SLEEPING_R_2: PixelGrid = decode_sprite([
    "................ddddaadd",
    "...............dddfaafddd",
    "......ddddddddddffffffffdd",
    ".....dddddfffffdffffffffddd",
    "....ddddffffffffffddddffffdd",
    "...dddddfffffffffffdddffffdd",
    "..ddffffffffffffffffffffffdd",
    ".dddffffffffffffffffffffffdd",
    "ddffffffffffffffffffffffffdd",
    "ddffffffffffffffffffffffffdd",
    "ddbbbbffffffffffffffffbbbbdd",
    ".dbbbbffffffffffffffffbbbbd",
    "..ddbbbbbbbbbbbbbbbbbbbbdd",
    "..ddbbbbbbbbbbbbbbbbbbbbdd",
    ".....dwf............fwd",
    ".....dww............wwd",
], _PIG_CHAR, width=28)

_CLOSE_HAPPY_R_2: PixelGrid = decode_sprite([
    "",
    "................ddddaadd",
    "....ddddddddddddddfaafddd",
    "...ddssssssssssdffffffffdd",
    "..ddsffffffffffffffssssfddd",
    ".ddsffffffffffffffsppppsffdd",
    "ddffffffffffffffffppppppfffd",
    "dfffffffffffffffffpsssspfnnd",
    "dffffffffffffffffffffffffnnd",
    "dfffffffffffffffffffffffffdd",
    ".dfffffffffffffffffffff...d",
    "..ddsffffffffffffffffff..dd",
    "...dsfffffffffffffffffffdd",
    "...dddsffsdddddddssfffdd",
    ".....dsfdd.......dddsfd",
    ".....dddd..........dddd",
], _PIG_CHAR, width=28)


# Build combined dict — right-facing raw grids mapped to all states
PIG_PIXELS_CLOSE_ADULT: dict[str, PixelGrid] = build_mirrored_dict({
    "idle_right":            _CLOSE_IDLE_R,
    "walking_right_1":       _CLOSE_WALKING_R_1,
    "eating_right_1":        _CLOSE_EATING_R_1,
    "sleeping_right_1":      _CLOSE_SLEEPING_R_1,
    "happy_right_1":         _CLOSE_HAPPY_R_1,
    "sad_right":             _CLOSE_SAD_R,
    "walking_right_2":       _CLOSE_WALKING_R_2,
    "walking_right_3":       _CLOSE_WALKING_R_3,
    "eating_right_2":        _CLOSE_EATING_R_2,
    "sleeping_right_2":      _CLOSE_SLEEPING_R_2,
    "happy_right_2":         _CLOSE_HAPPY_R_2,
})


# ---------------------------------------------------------------------------
# Baby close-zoom sprites (16w × 12h)
#
# Same approach: silhouette matches 2x-scaled, interior refined.
# ---------------------------------------------------------------------------

_BABY_IDLE_R: PixelGrid = decode_sprite([
    "........ddaadd",
    ".......dddfaafd",
    "..ddddddffffffdd",
    "..ddfffdffffffdd",
    "..ddffffeeppffdd",
    ".dddffffeepppfdd",
    "ddbbffffeeeenndd",
    ".dbbbfffeeeefnd",
    "..ddbbbbbbbbdd",
    "..ddbbbbbbbbdd",
    "...dwf....fwd",
    "...dww....wwd",
], _PIG_CHAR, width=16)

_BABY_WALKING_R_1: PixelGrid = decode_sprite([
    "........ddaadd",
    ".......dddfaafd",
    "..ddddddffffffdd",
    "..ddfffdffffffdd",
    "..ddffffeeppffdd",
    ".dddffffeepppfdd",
    "ddbbffffeeeenndd",
    ".dbbbfffeeeefnd",
    "..ddbbbbbbbbdd",
    "..ddbbbbbbbbdd",
    ".dwf........fwd",
    ".dww........wwd",
], _PIG_CHAR, width=16)

_BABY_SLEEPING_R_1: PixelGrid = decode_sprite([
    "........ddaadd",
    ".......dddfaafd",
    "..ddddddffffffdd",
    "..ddfffdffffffdd",
    "..ddffffddddffdd",
    ".dddffffdddddfdd",
    "ddbbffffffffffdd",
    ".dbbffffffffffd",
    "..ddbbbbbbbbdd",
    "..ddbbbbbbbbdd",
    "...dwf....fwd",
    "...dww....wwd",
], _PIG_CHAR, width=16)

_BABY_WALKING_R_2: PixelGrid = decode_sprite([
    "........dd..dd",
    "........dd..dd",
    "..ddddddffaaffdd",
    "..ddfffdffaaffdd",
    "..ddffffeeppffdd",
    ".dddffffeepppfdd",
    "ddbbffffeeeenndd",
    ".dbbbfffeeeefnd",
    "..ddbbbbbbbbdd",
    "..ddbbbbbbbbdd",
    "...dwf....fwd",
    "...dww....wwd",
], _PIG_CHAR, width=16)

_BABY_WALKING_R_3: PixelGrid = decode_sprite([
    "........ddaadd",
    ".......dddfaafd",
    "..ddddddffffffdd",
    "..ddfffdffffffdd",
    "..ddffffeeppffdd",
    ".dddffffeepppfdd",
    "ddbbffffeeeenndd",
    ".dbbbfffeeeefnd",
    "..ddbbbbbbbbdd",
    "..ddbbbbbbbbdd",
    "....dwwddwwd",
    "....ddddddd",
], _PIG_CHAR, width=16)

_BABY_SLEEPING_R_2: PixelGrid = decode_sprite([
    "........ddaadd",
    ".......dddfaafd",
    "..ddddddffffffdd",
    "..ddfffdffffffdd",
    "..ddffffddddffdd",
    ".dddffffdddddfdd",
    "ddbbbbffffffbbdd",
    "ddbbbbffffffbbdd",
    "ddbbbbbbbbbbbbdd",
    "ddbbbbbbbbbbbbdd",
    "...dwf....fwd",
    "...dww....wwd",
], _PIG_CHAR, width=16)


# Build combined dict — right-facing raw grids mapped to all states
PIG_PIXELS_CLOSE_BABY: dict[str, PixelGrid] = build_mirrored_dict({
    "idle_right":            _BABY_IDLE_R,
    "walking_right_1":       _BABY_WALKING_R_1,
    "sleeping_right_1":      _BABY_SLEEPING_R_1,
    "walking_right_2":       _BABY_WALKING_R_2,
    "walking_right_3":       _BABY_WALKING_R_3,
    "sleeping_right_2":      _BABY_SLEEPING_R_2,
})

# fmt: on
