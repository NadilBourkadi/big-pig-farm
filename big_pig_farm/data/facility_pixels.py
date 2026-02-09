"""Half-block pixel art data for facility sprites.

Each facility gets:
- A color palette mapping palette keys -> Rich color strings
- Normal-zoom pixel grids (8-12 wide x 6-8 tall) with state variants for consumables
- Far-zoom pixel grids (3-6 wide x 4-6 tall) for compact icons

Uses the same PixelGrid / convert_pixels() pipeline as pig sprites.
"""

from typing import Optional

# Transparent sentinel (matches sprite_pixels.py)
T = None

# Type alias for clarity (same as sprite_pixels.py)
PixelGrid = list[list[Optional[str]]]

# ---------------------------------------------------------------------------
# Color palettes — one per facility type
# ---------------------------------------------------------------------------

FACILITY_PALETTES: dict[str, dict[str, str]] = {
    "food_bowl": {
        "frame":  "#8B4513",     # saddle brown rim
        "bowl":   "#D2691E",     # chocolate bowl interior
        "food":   "#DAA520",     # goldenrod pellets
        "empty":  "#5C4033",     # dark brown empty slot
        "base":   "#6B3A2A",     # darker base
    },
    "water_bottle": {
        "frame":  "#A0A0A0",     # silver frame
        "glass":  "#B0C4DE",     # light steel blue glass
        "water":  "#4169E1",     # royal blue water
        "empty":  "#87CEEB",     # light empty glass
        "cap":    "#808080",     # grey cap
        "nozzle": "#C0C0C0",     # silver nozzle
        "drop":   "#00BFFF",     # deep sky blue drip
    },
    "hay_rack": {
        "frame":  "#8B7355",     # wood brown frame
        "hay":    "#DAA520",     # goldenrod hay
        "straw":  "#F0E68C",     # khaki light straw
        "empty":  "#6B5B3A",     # dark empty rack
        "slat":   "#A0522D",     # sienna wood slat
    },
    "hideout": {
        "frame":  "#654321",     # dark wood outline
        "roof":   "#8B4513",     # saddle brown roof
        "wall":   "#A0522D",     # sienna walls
        "door":   "#2F1B0E",     # very dark doorway
        "plank":  "#CD853F",     # peru wood planks
    },
    "exercise_wheel": {
        "frame":  "#696969",     # dim grey frame
        "wheel":  "#A9A9A9",     # dark grey wheel
        "spoke":  "#C0C0C0",     # silver spokes
        "axle":   "#808080",     # grey axle
        "stand":  "#555555",     # darker stand
    },
    "tunnel": {
        "frame":  "#556B2F",     # dark olive green
        "tube":   "#6B8E23",     # olive drab tube
        "open":   "#2F4F2F",     # dark green opening
        "ridge":  "#8FBC8F",     # dark sea green ridges
    },
    "play_area": {
        "frame":  "#D2691E",     # chocolate fence
        "fence":  "#DEB887",     # burlywood fence rails
        "ball":   "#FF6347",     # tomato red ball
        "block":  "#4169E1",     # royal blue block
        "grass":  "#228B22",     # forest green floor
        "star":   "#FFD700",     # gold star
    },
    "breeding_den": {
        "frame":  "#8B4513",     # wood brown
        "wall":   "#BC8F8F",     # rosy brown wall
        "heart":  "#FF69B4",     # hot pink heart
        "cushion":"#DDA0DD",     # plum cushion
        "roof":   "#CD853F",     # peru roof
    },
    "nursery": {
        "frame":  "#B0C4DE",     # light steel blue
        "wall":   "#E6E6FA",     # lavender wall
        "star":   "#FFD700",     # gold star
        "blanket":"#FFB6C1",     # light pink blanket
        "mobile": "#DDA0DD",     # plum mobile
        "rail":   "#87CEEB",     # sky blue rails
    },
    "veggie_garden": {
        "frame":  "#8B4513",     # wood brown border
        "soil":   "#5C4033",     # dark brown soil
        "leaf":   "#228B22",     # forest green leaves
        "veggie": "#FF6347",     # tomato veggie
        "stem":   "#2E8B57",     # sea green stems
        "carrot": "#FF8C00",     # dark orange carrot
    },
    "grooming_station": {
        "frame":  "#A9A9A9",     # dark grey frame
        "mirror": "#E0E0E0",     # light grey mirror
        "brush":  "#DEB887",     # burlywood brush
        "shine":  "#FFFFFF",     # white shine
        "base":   "#808080",     # grey base
    },
    "genetics_lab": {
        "frame":  "#4B0082",     # indigo frame
        "flask":  "#E0E0E0",     # light grey flask
        "liquid": "#00CED1",     # dark turquoise liquid
        "dna":    "#9370DB",     # medium purple dna helix
        "glow":   "#7FFFD4",     # aquamarine glow
        "base":   "#2F0052",     # very dark purple base
    },
}


# ---------------------------------------------------------------------------
# Normal-zoom pixel grids
# ---------------------------------------------------------------------------
# Keyed by "{facility_type}" or "{facility_type}_{state}" for state variants.
# Consumables have "default", "empty", "full" states.
# All others have only "default".

# fmt: off

FACILITY_PIXELS: dict[str, PixelGrid] = {
    # -----------------------------------------------------------------------
    # FOOD BOWL  (8w x 6h -> 8x3 half-block)
    # -----------------------------------------------------------------------
    "food_bowl": [
        [ T,    "frame","frame","frame","frame","frame","frame", T    ],
        ["frame","bowl", "bowl", "bowl", "bowl", "bowl", "bowl","frame"],
        ["frame","food", "food", "food", "food", "empty","empty","frame"],
        ["frame","food", "food", "food", "food", "empty","empty","frame"],
        ["frame","base", "bowl", "bowl", "bowl", "bowl", "base","frame"],
        [ T,    "frame","frame","frame","frame","frame","frame", T    ],
    ],
    "food_bowl_empty": [
        [ T,    "frame","frame","frame","frame","frame","frame", T    ],
        ["frame","bowl", "bowl", "bowl", "bowl", "bowl", "bowl","frame"],
        ["frame","empty","empty","empty","empty","empty","empty","frame"],
        ["frame","empty","empty","empty","empty","empty","empty","frame"],
        ["frame","base", "bowl", "bowl", "bowl", "bowl", "base","frame"],
        [ T,    "frame","frame","frame","frame","frame","frame", T    ],
    ],
    "food_bowl_full": [
        [ T,    "frame","frame","frame","frame","frame","frame", T    ],
        ["frame","bowl", "bowl", "bowl", "bowl", "bowl", "bowl","frame"],
        ["frame","food", "food", "food", "food", "food", "food","frame"],
        ["frame","food", "food", "food", "food", "food", "food","frame"],
        ["frame","base", "bowl", "bowl", "bowl", "bowl", "base","frame"],
        [ T,    "frame","frame","frame","frame","frame","frame", T    ],
    ],

    # -----------------------------------------------------------------------
    # WATER BOTTLE  (5w x 10h -> 5x5 half-block)
    # -----------------------------------------------------------------------
    "water_bottle": [
        [ T,   "cap",  "cap",  "cap",   T    ],
        ["frame","glass","glass","glass","frame"],
        ["frame","water","water","water","frame"],
        ["frame","water","water","water","frame"],
        ["frame","water","water","water","frame"],
        ["frame","glass","glass","glass","frame"],
        ["frame","glass","glass","glass","frame"],
        ["frame","frame","frame","frame","frame"],
        [ T,    T,    "nozzle", T,    T    ],
        [ T,    T,    "drop",   T,    T    ],
    ],
    "water_bottle_empty": [
        [ T,   "cap",  "cap",  "cap",   T    ],
        ["frame","glass","glass","glass","frame"],
        ["frame","empty","empty","empty","frame"],
        ["frame","empty","empty","empty","frame"],
        ["frame","empty","empty","empty","frame"],
        ["frame","empty","empty","empty","frame"],
        ["frame","glass","glass","glass","frame"],
        ["frame","frame","frame","frame","frame"],
        [ T,    T,    "nozzle", T,    T    ],
        [ T,    T,     T,      T,    T    ],
    ],
    "water_bottle_full": [
        [ T,   "cap",  "cap",  "cap",   T    ],
        ["frame","glass","glass","glass","frame"],
        ["frame","water","water","water","frame"],
        ["frame","water","water","water","frame"],
        ["frame","water","water","water","frame"],
        ["frame","water","water","water","frame"],
        ["frame","glass","glass","glass","frame"],
        ["frame","frame","frame","frame","frame"],
        [ T,    T,    "nozzle", T,    T    ],
        [ T,    T,    "drop",   T,    T    ],
    ],

    # -----------------------------------------------------------------------
    # HAY RACK  (7w x 6h -> 7x3 half-block)
    # -----------------------------------------------------------------------
    "hay_rack": [
        ["frame","slat", "frame","frame","frame","slat","frame"],
        ["frame","hay",  "hay",  "straw","hay",  "hay","frame"],
        ["frame","hay",  "straw","hay",  "straw","hay","frame"],
        ["frame","hay",  "hay",  "hay",  "hay",  "hay","frame"],
        ["frame","slat", "hay",  "hay",  "hay",  "slat","frame"],
        ["frame","frame","frame","frame","frame","frame","frame"],
    ],
    "hay_rack_empty": [
        ["frame","slat", "frame","frame","frame","slat","frame"],
        ["frame","empty","empty","empty","empty","empty","frame"],
        ["frame","empty","empty","empty","empty","empty","frame"],
        ["frame","empty","empty","empty","empty","empty","frame"],
        ["frame","slat", "empty","empty","empty","slat","frame"],
        ["frame","frame","frame","frame","frame","frame","frame"],
    ],
    "hay_rack_full": [
        ["frame","slat", "frame","frame","frame","slat","frame"],
        ["frame","hay",  "hay",  "hay",  "hay",  "hay","frame"],
        ["frame","straw","hay",  "straw","hay",  "straw","frame"],
        ["frame","hay",  "straw","hay",  "straw","hay","frame"],
        ["frame","slat", "hay",  "hay",  "hay",  "slat","frame"],
        ["frame","frame","frame","frame","frame","frame","frame"],
    ],

    # -----------------------------------------------------------------------
    # HIDEOUT  (10w x 6h -> 10x3 half-block)
    # -----------------------------------------------------------------------
    "hideout": [
        [ T,   "frame","roof", "roof", "roof", "roof", "roof", "roof","frame", T    ],
        ["frame","roof", "roof", "plank","roof", "roof", "plank","roof","roof","frame"],
        ["frame","wall", "wall", "wall", "wall", "wall", "wall", "wall","wall","frame"],
        ["frame","wall", "wall", "wall", "door", "door", "wall", "wall","wall","frame"],
        ["frame","wall", "plank","wall", "door", "door", "wall", "plank","wall","frame"],
        ["frame","frame","frame","frame","frame","frame","frame","frame","frame","frame"],
    ],

    # -----------------------------------------------------------------------
    # EXERCISE WHEEL  (9w x 6h -> 9x3 half-block)
    # -----------------------------------------------------------------------
    "exercise_wheel": [
        [ T,    T,   "frame","wheel","wheel","wheel","frame", T,    T    ],
        [ T,   "frame","wheel","spoke","wheel","spoke","wheel","frame", T    ],
        ["frame","wheel","wheel","wheel","axle", "wheel","wheel","wheel","frame"],
        [ T,   "frame","wheel","spoke","wheel","spoke","wheel","frame", T    ],
        [ T,    T,   "frame","wheel","wheel","wheel","frame", T,    T    ],
        [ T,    T,    T,   "stand","stand","stand", T,    T,    T    ],
    ],

    # -----------------------------------------------------------------------
    # TUNNEL  (7w x 6h -> 7x3 half-block)
    # -----------------------------------------------------------------------
    "tunnel": [
        ["frame","ridge","tube", "tube", "tube","ridge","frame"],
        ["open", "tube", "tube", "tube", "tube", "tube","open" ],
        ["frame","tube", "tube", "ridge","tube", "tube","frame"],
        ["frame","tube", "tube", "ridge","tube", "tube","frame"],
        ["open", "tube", "tube", "tube", "tube", "tube","open" ],
        ["frame","ridge","tube", "tube", "tube","ridge","frame"],
    ],

    # -----------------------------------------------------------------------
    # PLAY AREA  (9w x 8h -> 9x4 half-block)
    # -----------------------------------------------------------------------
    "play_area": [
        ["frame","fence","fence","fence","fence","fence","fence","fence","frame"],
        ["frame","grass","grass","grass","grass","grass","grass","grass","frame"],
        ["frame","grass","ball", "grass","grass","grass","block","grass","frame"],
        ["frame","grass","grass","grass","star", "grass","grass","grass","frame"],
        ["frame","grass","grass","grass","grass","grass","grass","grass","frame"],
        ["frame","grass","block","grass","grass","grass","ball", "grass","frame"],
        ["frame","grass","grass","grass","grass","grass","grass","grass","frame"],
        ["frame","fence","fence","fence","fence","fence","fence","fence","frame"],
    ],

    # -----------------------------------------------------------------------
    # BREEDING DEN  (8w x 6h -> 8x3 half-block)
    # -----------------------------------------------------------------------
    "breeding_den": [
        [ T,   "frame","roof", "roof", "roof", "roof","frame", T    ],
        ["frame","wall", "wall", "wall", "wall", "wall","wall","frame"],
        ["frame","wall","cushion","wall","wall","cushion","wall","frame"],
        ["frame","wall", "wall","heart","heart","wall", "wall","frame"],
        ["frame","wall","cushion","wall","wall","cushion","wall","frame"],
        [ T,   "frame","frame","frame","frame","frame","frame", T    ],
    ],

    # -----------------------------------------------------------------------
    # NURSERY  (10w x 8h -> 10x4 half-block)
    # -----------------------------------------------------------------------
    "nursery": [
        ["frame","rail", "rail", "rail", "rail", "rail", "rail", "rail","rail","frame"],
        ["frame","wall", "wall", "wall","mobile","mobile","wall", "wall","wall","frame"],
        ["frame","wall", "wall", "star", "wall", "wall", "star", "wall","wall","frame"],
        ["frame","wall", "wall", "wall", "wall", "wall", "wall", "wall","wall","frame"],
        ["frame","wall", "wall", "wall", "wall", "wall", "wall", "wall","wall","frame"],
        ["frame","wall","blanket","blanket","blanket","blanket","blanket","blanket","wall","frame"],
        ["frame","wall","blanket","blanket","blanket","blanket","blanket","blanket","wall","frame"],
        ["frame","rail", "rail", "rail", "rail", "rail", "rail", "rail","rail","frame"],
    ],

    # -----------------------------------------------------------------------
    # VEGGIE GARDEN  (9w x 8h -> 9x4 half-block)
    # -----------------------------------------------------------------------
    "veggie_garden": [
        ["frame","frame","frame","frame","frame","frame","frame","frame","frame"],
        ["frame","soil", "leaf", "soil", "stem", "soil", "leaf", "soil","frame"],
        ["frame","soil", "stem", "soil", "leaf", "soil", "stem", "soil","frame"],
        ["frame","leaf","carrot","leaf","veggie","leaf","carrot","leaf","frame"],
        ["frame","soil", "stem", "soil", "stem", "soil", "stem", "soil","frame"],
        ["frame","leaf", "soil","carrot","soil","carrot","soil", "leaf","frame"],
        ["frame","soil", "leaf", "soil", "leaf", "soil", "leaf", "soil","frame"],
        ["frame","frame","frame","frame","frame","frame","frame","frame","frame"],
    ],

    # -----------------------------------------------------------------------
    # GROOMING STATION  (7w x 6h -> 7x3 half-block)
    # -----------------------------------------------------------------------
    "grooming_station": [
        [ T,   "frame","frame","frame","frame","frame", T    ],
        ["frame","mirror","mirror","shine","mirror","mirror","frame"],
        ["frame","mirror","mirror","mirror","mirror","mirror","frame"],
        ["frame","base", "base", "base", "base", "base","frame"],
        ["frame","base", "brush","base", "brush","base","frame"],
        [ T,   "frame","frame","frame","frame","frame", T    ],
    ],

    # -----------------------------------------------------------------------
    # GENETICS LAB  (11w x 8h -> 11x4 half-block)
    # -----------------------------------------------------------------------
    "genetics_lab": [
        ["frame","frame","frame","frame","frame","frame","frame","frame","frame","frame","frame"],
        ["frame","base", "flask","flask","base", "dna", "base", "flask","flask","base","frame"],
        ["frame","base", "flask","liquid","base","dna", "base","liquid","flask","base","frame"],
        ["frame","base", "flask","liquid","base","glow", "base","liquid","flask","base","frame"],
        ["frame","base", "base", "base", "dna", "dna", "dna", "base", "base", "base","frame"],
        ["frame","base", "glow", "base", "base","dna", "base", "base", "glow","base","frame"],
        ["frame","base", "base", "base", "base", "base", "base", "base", "base","base","frame"],
        ["frame","frame","frame","frame","frame","frame","frame","frame","frame","frame","frame"],
    ],
}


# ---------------------------------------------------------------------------
# Far-zoom pixel grids (compact icons for zoomed-out view)
# ---------------------------------------------------------------------------

FACILITY_PIXELS_FAR: dict[str, PixelGrid] = {
    # FOOD BOWL (4w x 4h -> 4x2)
    "food_bowl": [
        [ T,   "frame","frame", T    ],
        ["frame","food", "food","frame"],
        ["frame","bowl", "bowl","frame"],
        [ T,   "frame","frame", T    ],
    ],
    # WATER BOTTLE (3w x 6h -> 3x3)
    "water_bottle": [
        ["frame","cap",  "frame"],
        ["frame","water","frame"],
        ["frame","water","frame"],
        ["frame","water","frame"],
        ["frame","frame","frame"],
        [ T,   "nozzle", T    ],
    ],
    # HAY RACK (4w x 4h -> 4x2)
    "hay_rack": [
        ["frame","frame","frame","frame"],
        ["frame","hay",  "straw","frame"],
        ["frame","hay",  "hay", "frame"],
        ["frame","frame","frame","frame"],
    ],
    # HIDEOUT (5w x 4h -> 5x2)
    "hideout": [
        [ T,   "roof", "roof", "roof",  T    ],
        ["frame","wall", "wall", "wall","frame"],
        ["frame","wall", "door", "wall","frame"],
        ["frame","frame","frame","frame","frame"],
    ],
    # EXERCISE WHEEL (5w x 4h -> 5x2)
    "exercise_wheel": [
        [ T,   "wheel","wheel","wheel", T    ],
        ["frame","spoke","axle","spoke","frame"],
        [ T,   "wheel","wheel","wheel", T    ],
        [ T,    T,   "stand", T,    T    ],
    ],
    # TUNNEL (5w x 4h -> 5x2)
    "tunnel": [
        ["frame","tube", "tube", "tube","frame"],
        ["open", "tube", "tube", "tube","open" ],
        ["frame","tube", "tube", "tube","frame"],
        ["open", "tube", "tube", "tube","open" ],
    ],
    # PLAY AREA (5w x 4h -> 5x2)
    "play_area": [
        ["fence","fence","fence","fence","fence"],
        ["grass","ball", "grass","block","grass"],
        ["grass","grass","star", "grass","grass"],
        ["fence","fence","fence","fence","fence"],
    ],
    # BREEDING DEN (4w x 4h -> 4x2)
    "breeding_den": [
        ["frame","roof", "roof","frame"],
        ["frame","wall","heart","frame"],
        ["frame","cushion","wall","frame"],
        ["frame","frame","frame","frame"],
    ],
    # NURSERY (5w x 4h -> 5x2)
    "nursery": [
        ["rail", "rail", "rail", "rail","rail" ],
        ["wall", "star", "wall", "star","wall" ],
        ["wall","blanket","blanket","blanket","wall"],
        ["rail", "rail", "rail", "rail","rail" ],
    ],
    # VEGGIE GARDEN (5w x 4h -> 5x2)
    "veggie_garden": [
        ["frame","frame","frame","frame","frame"],
        ["soil", "leaf", "stem", "leaf","soil" ],
        ["leaf","carrot","veggie","carrot","leaf"],
        ["frame","frame","frame","frame","frame"],
    ],
    # GROOMING STATION (4w x 4h -> 4x2)
    "grooming_station": [
        ["frame","frame","frame","frame"],
        ["frame","mirror","shine","frame"],
        ["frame","base", "brush","frame"],
        ["frame","frame","frame","frame"],
    ],
    # GENETICS LAB (5w x 4h -> 5x2)
    "genetics_lab": [
        ["frame","frame","frame","frame","frame"],
        ["base", "flask","dna", "flask","base" ],
        ["base","liquid","glow","liquid","base" ],
        ["frame","frame","frame","frame","frame"],
    ],
}

# fmt: on
