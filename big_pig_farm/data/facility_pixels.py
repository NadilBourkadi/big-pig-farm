"""Half-block pixel art data for facility sprites.

Each facility gets:
- A color palette mapping palette keys -> Rich color strings
- Normal-zoom pixel grids (8-12 wide x 6-10 tall) with state variants for consumables
- Far-zoom pixel grids (3-6 wide x 4-6 tall) for compact icons

Uses the same PixelGrid / convert_pixels() pipeline as pig sprites.
"""

from big_pig_farm.data.sprite_engine import PixelGrid, T

# ---------------------------------------------------------------------------
# Color palettes — one per facility type
# ---------------------------------------------------------------------------

FACILITY_PALETTES: dict[str, dict[str, str]] = {
    "food_bowl": {
        "frame":  "#A0582A",     # warm brown rim
        "bowl":   "#CD853F",     # peru bowl interior (lighter for contrast)
        "food":   "#DAA520",     # goldenrod pellets
        "empty":  "#5C4033",     # dark brown empty slot
        "base":   "#6B3A2A",     # darker base
    },
    "water_bottle": {
        "frame":  "#B8B8B8",     # light silver frame
        "glass":  "#B0C4DE",     # light steel blue glass
        "water":  "#4169E1",     # royal blue water
        "empty":  "#87CEEB",     # light empty glass
        "cap":    "#808080",     # grey cap
        "nozzle": "#C0C0C0",     # silver nozzle
        "drop":   "#00BFFF",     # deep sky blue drip
    },
    "hay_rack": {
        "frame":  "#A08868",     # wood brown frame
        "hay":    "#DAA520",     # goldenrod hay
        "straw":  "#F0E68C",     # khaki light straw
        "empty":  "#6B5B3A",     # dark empty rack
        "slat":   "#A0522D",     # sienna wood slat
    },
    "hideout": {
        "frame":  "#7A5838",     # wood outline
        "roof":   "#8B4513",     # saddle brown roof
        "wall":   "#A0522D",     # sienna walls
        "door":   "#2F1B0E",     # very dark doorway
        "plank":  "#CD853F",     # peru wood planks
    },
    "exercise_wheel": {
        "frame":  "#808080",     # grey frame
        "wheel":  "#A9A9A9",     # dark grey wheel
        "spoke":  "#C0C0C0",     # silver spokes
        "axle":   "#808080",     # grey axle
        "stand":  "#555555",     # darker stand
    },
    "tunnel": {
        "frame":  "#6B8040",     # olive green
        "tube":   "#6B8E23",     # olive drab tube
        "open":   "#2F4F2F",     # dark green opening
        "ridge":  "#8FBC8F",     # dark sea green ridges
    },
    "play_area": {
        "frame":  "#E07830",     # warm fence
        "fence":  "#DEB887",     # burlywood fence rails
        "ball":   "#FF6347",     # tomato red ball
        "block":  "#4169E1",     # royal blue block
        "grass":  "#228B22",     # forest green floor
        "star":   "#FFD700",     # gold star
    },
    "breeding_den": {
        "frame":  "#A0582A",     # warm brown
        "wall":   "#BC8F8F",     # rosy brown wall
        "heart":  "#FF69B4",     # hot pink heart
        "cushion":"#DDA0DD",     # plum cushion
        "roof":   "#CD853F",     # peru roof
    },
    "nursery": {
        "frame":  "#C4D8F0",     # soft blue
        "wall":   "#E6E6FA",     # lavender wall
        "star":   "#FFD700",     # gold star
        "blanket":"#FFB6C1",     # light pink blanket
        "mobile": "#DDA0DD",     # plum mobile
        "rail":   "#87CEEB",     # sky blue rails
    },
    "veggie_garden": {
        "frame":  "#A0582A",     # warm brown border
        "soil":   "#5C4033",     # dark brown soil
        "leaf":   "#228B22",     # forest green leaves
        "veggie": "#FF6347",     # tomato veggie
        "stem":   "#2E8B57",     # sea green stems
        "carrot": "#FF8C00",     # dark orange carrot
    },
    "grooming_station": {
        "frame":  "#C0C0C0",     # silver frame
        "mirror": "#B0C4DE",     # light steel blue mirror (cooler tone)
        "brush":  "#DEB887",     # burlywood brush
        "shine":  "#FFFFFF",     # white shine
        "base":   "#808080",     # grey base
        "stand":  "#696969",     # dim grey stand pole
    },
    "genetics_lab": {
        "frame":  "#5C1A98",     # purple frame
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
    # FOOD BOWL  (8w x 6h -> 8x3)  —  curved U-shape with food pellets
    # -----------------------------------------------------------------------
    "food_bowl": [
        [ T,   "frame","frame","frame","frame","frame","frame", T    ],
        ["frame","bowl", "bowl", "bowl", "bowl", "bowl", "bowl","frame"],
        ["frame","food", "food", "food", "food", "empty","empty","frame"],
        ["frame","food", "food", "food", "food", "empty","empty","frame"],
        [ T,   "frame","base", "bowl", "bowl", "base","frame", T    ],
        [ T,    T,   "frame","frame","frame","frame", T,    T    ],
    ],
    "food_bowl_empty": [
        [ T,   "frame","frame","frame","frame","frame","frame", T    ],
        ["frame","bowl", "bowl", "bowl", "bowl", "bowl", "bowl","frame"],
        ["frame","empty","empty","empty","empty","empty","empty","frame"],
        ["frame","empty","empty","empty","empty","empty","empty","frame"],
        [ T,   "frame","base", "bowl", "bowl", "base","frame", T    ],
        [ T,    T,   "frame","frame","frame","frame", T,    T    ],
    ],
    "food_bowl_full": [
        [ T,   "frame","frame","frame","frame","frame","frame", T    ],
        ["frame","bowl", "food", "food", "food", "food", "bowl","frame"],
        ["frame","food", "food", "food", "food", "food", "food","frame"],
        ["frame","food", "food", "food", "food", "food", "food","frame"],
        [ T,   "frame","base", "bowl", "bowl", "base","frame", T    ],
        [ T,    T,   "frame","frame","frame","frame", T,    T    ],
    ],

    # -----------------------------------------------------------------------
    # WATER BOTTLE  (5w x 10h -> 5x5)  —  tall bottle with nozzle drip
    # Unchanged — user says this size is right.
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
    # HAY RACK  (8w x 8h -> 8x4)  —  hay wisps poking above the frame
    # -----------------------------------------------------------------------
    "hay_rack": [
        [ T,    T,   "hay", "straw","hay", "straw", T,    T    ],
        [ T,   "hay", "straw","hay", "hay", "straw","hay",  T   ],
        ["frame","slat","frame","frame","frame","frame","slat","frame"],
        ["frame","hay", "hay", "straw","hay", "straw","hay","frame"],
        ["frame","hay", "straw","hay", "straw","hay", "hay","frame"],
        ["frame","hay", "hay", "hay", "hay", "hay", "hay","frame"],
        ["frame","slat","hay", "hay", "hay", "hay","slat","frame"],
        ["frame","frame","frame","frame","frame","frame","frame","frame"],
    ],
    "hay_rack_empty": [
        [ T,    T,    T,    T,    T,    T,    T,    T    ],
        [ T,    T,    T,    T,    T,    T,    T,    T    ],
        ["frame","slat","frame","frame","frame","frame","slat","frame"],
        ["frame","empty","empty","empty","empty","empty","empty","frame"],
        ["frame","empty","empty","empty","empty","empty","empty","frame"],
        ["frame","empty","empty","empty","empty","empty","empty","frame"],
        ["frame","slat","empty","empty","empty","empty","slat","frame"],
        ["frame","frame","frame","frame","frame","frame","frame","frame"],
    ],
    "hay_rack_full": [
        [ T,   "straw","hay", "straw","hay", "straw","hay",  T   ],
        ["hay", "straw","hay", "hay", "straw","hay", "straw","hay"],
        ["frame","slat","frame","frame","frame","frame","slat","frame"],
        ["frame","hay", "straw","hay", "straw","hay", "straw","frame"],
        ["frame","straw","hay", "straw","hay", "straw","hay","frame"],
        ["frame","hay", "hay", "hay", "hay", "hay", "hay","frame"],
        ["frame","slat","hay", "hay", "hay", "hay","slat","frame"],
        ["frame","frame","frame","frame","frame","frame","frame","frame"],
    ],

    # -----------------------------------------------------------------------
    # HIDEOUT  (11w x 8h -> 11x4)  —  peaked triangular roof + dark doorway
    # -----------------------------------------------------------------------
    "hideout": [
        [ T,    T,    T,    T,    T,   "roof",  T,    T,    T,    T,    T    ],
        [ T,    T,    T,   "frame","roof","roof","roof","frame", T,    T,    T    ],
        [ T,    T,   "frame","roof","roof","plank","roof","roof","frame", T,    T    ],
        [ T,   "frame","roof","roof","plank","roof","roof","plank","roof","frame", T    ],
        ["frame","wall","wall","wall","wall","wall","wall","wall","wall","wall","frame"],
        ["frame","wall","plank","wall","wall","door","wall","wall","plank","wall","frame"],
        ["frame","wall","wall","wall","door","door","door","wall","wall","wall","frame"],
        ["frame","frame","frame","frame","frame","frame","frame","frame","frame","frame","frame"],
    ],

    # -----------------------------------------------------------------------
    # EXERCISE WHEEL  (9w x 8h -> 9x4)  —  circular wheel on A-frame stand
    # -----------------------------------------------------------------------
    "exercise_wheel": [
        [ T,    T,   "frame","wheel","wheel","wheel","frame", T,    T    ],
        [ T,   "frame","wheel","spoke","wheel","spoke","wheel","frame", T    ],
        ["frame","wheel","wheel","wheel","axle","wheel","wheel","wheel","frame"],
        [ T,   "frame","wheel","spoke","wheel","spoke","wheel","frame", T    ],
        [ T,    T,   "frame","wheel","wheel","wheel","frame", T,    T    ],
        [ T,   "stand","stand","frame","frame","frame","stand","stand", T    ],
        [ T,   "stand", T,    T,   "stand", T,    T,   "stand", T    ],
        [ T,    T,    T,    T,   "stand", T,    T,    T,    T    ],
    ],

    # -----------------------------------------------------------------------
    # TUNNEL  (9w x 6h -> 9x3)  —  wider horizontal tube with dark openings
    # -----------------------------------------------------------------------
    "tunnel": [
        [ T,   "frame","ridge","tube","tube","tube","ridge","frame", T    ],
        ["open","tube", "tube","tube","tube","tube","tube", "tube","open" ],
        ["frame","tube","tube","ridge","tube","ridge","tube","tube","frame"],
        ["frame","tube","tube","ridge","tube","ridge","tube","tube","frame"],
        ["open","tube", "tube","tube","tube","tube","tube", "tube","open" ],
        [ T,   "frame","ridge","tube","tube","tube","ridge","frame", T    ],
    ],

    # -----------------------------------------------------------------------
    # PLAY AREA  (10w x 8h -> 10x4)  —  fenced yard with scattered toys
    # -----------------------------------------------------------------------
    "play_area": [
        ["frame","fence","fence","fence","fence","fence","fence","fence","fence","frame"],
        ["frame","grass","grass","grass","grass","grass","grass","grass","grass","frame"],
        ["frame","grass","ball", "grass","grass","star","grass","block","grass","frame"],
        ["frame","grass","grass","grass","grass","grass","grass","grass","grass","frame"],
        ["frame","grass","grass","grass","grass","grass","grass","grass","grass","frame"],
        ["frame","grass","block","grass","star","grass","grass","ball", "grass","frame"],
        ["frame","grass","grass","grass","grass","grass","grass","grass","grass","frame"],
        ["frame","fence","fence","fence","fence","fence","fence","fence","fence","frame"],
    ],

    # -----------------------------------------------------------------------
    # BREEDING DEN  (9w x 8h -> 9x4)  —  cozy den with prominent heart
    # -----------------------------------------------------------------------
    "breeding_den": [
        [ T,   "frame","roof","roof","roof","roof","roof","frame", T    ],
        ["frame","wall","wall","wall","wall","wall","wall","wall","frame"],
        ["frame","wall","wall","heart","wall","heart","wall","wall","frame"],
        ["frame","wall","heart","heart","heart","heart","heart","wall","frame"],
        ["frame","wall","wall","heart","heart","heart","wall","wall","frame"],
        ["frame","wall","cushion","wall","heart","wall","cushion","wall","frame"],
        ["frame","wall","cushion","cushion","cushion","cushion","cushion","wall","frame"],
        [ T,   "frame","frame","frame","frame","frame","frame","frame", T    ],
    ],

    # -----------------------------------------------------------------------
    # NURSERY  (11w x 8h -> 11x4)  —  crib with rails, mobile, and blanket
    # -----------------------------------------------------------------------
    "nursery": [
        ["frame","rail","rail","rail","rail","rail","rail","rail","rail","rail","frame"],
        ["frame","wall","wall","wall","mobile","wall","mobile","wall","wall","wall","frame"],
        ["frame","wall","wall","star","wall","wall","wall","star","wall","wall","frame"],
        ["frame","wall","wall","wall","wall","wall","wall","wall","wall","wall","frame"],
        ["frame","wall","wall","wall","wall","wall","wall","wall","wall","wall","frame"],
        ["frame","wall","blanket","blanket","blanket","blanket","blanket","blanket","blanket","wall","frame"],
        ["frame","wall","blanket","blanket","blanket","blanket","blanket","blanket","blanket","wall","frame"],
        ["frame","rail","rail","rail","rail","rail","rail","rail","rail","rail","frame"],
    ],

    # -----------------------------------------------------------------------
    # VEGGIE GARDEN  (9w x 8h -> 9x4)  —  rows of veggies in soil
    # -----------------------------------------------------------------------
    "veggie_garden": [
        ["frame","frame","frame","frame","frame","frame","frame","frame","frame"],
        ["frame","soil","leaf","soil","stem","soil","leaf","soil","frame"],
        ["frame","stem","soil","leaf","soil","leaf","soil","stem","frame"],
        ["frame","leaf","carrot","leaf","veggie","leaf","carrot","leaf","frame"],
        ["frame","soil","stem","soil","stem","soil","stem","soil","frame"],
        ["frame","leaf","soil","carrot","soil","carrot","soil","leaf","frame"],
        ["frame","soil","leaf","soil","leaf","soil","leaf","soil","frame"],
        ["frame","frame","frame","frame","frame","frame","frame","frame","frame"],
    ],

    # -----------------------------------------------------------------------
    # GROOMING STATION  (9w x 8h -> 9x4)  —  oval mirror on stand + brush shelf
    # -----------------------------------------------------------------------
    "grooming_station": [
        [ T,    T,   "frame","frame","frame","frame","frame", T,    T    ],
        [ T,   "frame","mirror","mirror","shine","mirror","mirror","frame", T    ],
        [ T,   "frame","mirror","mirror","mirror","mirror","mirror","frame", T    ],
        [ T,    T,   "frame","frame","frame","frame","frame", T,    T    ],
        [ T,    T,    T,    T,   "stand", T,    T,    T,    T    ],
        [ T,   "frame","base","base","base","base","base","frame", T    ],
        [ T,   "frame","brush","base","base","base","brush","frame", T    ],
        [ T,   "frame","frame","frame","frame","frame","frame","frame", T    ],
    ],

    # -----------------------------------------------------------------------
    # GENETICS LAB  (11w x 8h -> 11x4)  —  flask shapes flanking DNA helix
    # -----------------------------------------------------------------------
    "genetics_lab": [
        ["frame","frame","frame","frame","frame","frame","frame","frame","frame","frame","frame"],
        ["frame","base","base","flask","base","dna","base","flask","base","base","frame"],
        ["frame","base","flask","flask","base","dna","base","flask","flask","base","frame"],
        ["frame","base","flask","liquid","base","glow","base","liquid","flask","base","frame"],
        ["frame","base","flask","liquid","dna","dna","dna","liquid","flask","base","frame"],
        ["frame","base","base","base","base","dna","base","base","base","base","frame"],
        ["frame","base","glow","base","base","dna","base","base","glow","base","frame"],
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
        ["frame","food","food","frame"],
        ["frame","bowl","bowl","frame"],
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
    # HAY RACK (5w x 4h -> 5x2)
    "hay_rack": [
        [ T,   "hay","straw","hay",  T    ],
        ["frame","frame","frame","frame","frame"],
        ["frame","hay","straw","hay","frame"],
        ["frame","frame","frame","frame","frame"],
    ],
    # HIDEOUT (5w x 4h -> 5x2)  —  peaked roof
    "hideout": [
        [ T,    T,   "roof",  T,    T    ],
        [ T,   "roof","roof","roof",  T   ],
        ["frame","wall","door","wall","frame"],
        ["frame","frame","frame","frame","frame"],
    ],
    # EXERCISE WHEEL (5w x 6h -> 5x3)  —  round wheel + stand
    "exercise_wheel": [
        [ T,   "wheel","wheel","wheel", T    ],
        ["frame","spoke","axle","spoke","frame"],
        [ T,   "wheel","wheel","wheel", T    ],
        [ T,   "stand","frame","stand", T    ],
        [ T,   "stand", T,   "stand", T    ],
        [ T,    T,   "stand", T,    T    ],
    ],
    # TUNNEL (5w x 4h -> 5x2)
    "tunnel": [
        ["frame","tube","tube","tube","frame"],
        ["open","tube","tube","tube","open" ],
        ["frame","tube","tube","tube","frame"],
        ["open","tube","tube","tube","open" ],
    ],
    # PLAY AREA (5w x 4h -> 5x2)
    "play_area": [
        ["fence","fence","fence","fence","fence"],
        ["grass","ball","grass","block","grass"],
        ["grass","grass","star","grass","grass"],
        ["fence","fence","fence","fence","fence"],
    ],
    # BREEDING DEN (5w x 4h -> 5x2)  —  visible heart
    "breeding_den": [
        ["frame","roof","roof","roof","frame"],
        ["wall","heart","wall","heart","wall"],
        ["wall","wall","heart","wall","wall"],
        ["frame","frame","frame","frame","frame"],
    ],
    # NURSERY (5w x 4h -> 5x2)
    "nursery": [
        ["rail","rail","rail","rail","rail"],
        ["wall","star","wall","star","wall"],
        ["wall","blanket","blanket","blanket","wall"],
        ["rail","rail","rail","rail","rail"],
    ],
    # VEGGIE GARDEN (5w x 4h -> 5x2)
    "veggie_garden": [
        ["frame","frame","frame","frame","frame"],
        ["soil","leaf","stem","leaf","soil" ],
        ["leaf","carrot","veggie","carrot","leaf"],
        ["frame","frame","frame","frame","frame"],
    ],
    # GROOMING STATION (5w x 4h -> 5x2)  —  mirror shape
    "grooming_station": [
        [ T,   "frame","shine","frame", T    ],
        [ T,   "frame","mirror","frame", T   ],
        [ T,    T,   "stand", T,    T    ],
        [ T,   "frame","brush","frame", T    ],
    ],
    # GENETICS LAB (5w x 4h -> 5x2)
    "genetics_lab": [
        ["frame","frame","frame","frame","frame"],
        ["base","flask","dna","flask","base" ],
        ["base","liquid","glow","liquid","base" ],
        ["frame","frame","frame","frame","frame"],
    ],
}

# fmt: on
