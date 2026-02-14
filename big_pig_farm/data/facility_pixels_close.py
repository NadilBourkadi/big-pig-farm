"""Hand-crafted close-zoom facility pixel sprites (2x normal dimensions).

Uses compact single-char encoding decoded at import time.
Each facility has its own char map matching its palette keys.
"""

from big_pig_farm.data.sprite_engine import PixelGrid, decode_sprite

# fmt: off

# ---------------------------------------------------------------------------
# FOOD BOWL (16w × 12h)  —  curved rim, pellet clusters, bowl bottom curve
# ---------------------------------------------------------------------------

_FOOD_BOWL_CHAR = {
    ".": None, "r": "frame", "b": "bowl", "f": "food", "e": "empty", "s": "base",
}

FACILITY_PIXELS_CLOSE: dict[str, PixelGrid] = {}

FACILITY_PIXELS_CLOSE["food_bowl"] = decode_sprite([
    "....rrrrrrrr....",
    "..rrbbbbbbbbrr..",
    ".rbbbbbbbbbbbbr.",
    "rbbbffffeeeebbbr",
    "rbbfffffeeeebbbr",
    "rbbfffffffffffbr",
    "rbbfffffffffffbr",
    "rbbffffeeeebbbr.",
    ".rbbbbbbbbbbbr..",
    "..rrssbbbbssrr..",
    "....rrrrrrrr....",
    "................",
], _FOOD_BOWL_CHAR, width=16)

FACILITY_PIXELS_CLOSE["food_bowl_empty"] = decode_sprite([
    "....rrrrrrrr....",
    "..rrbbbbbbbbrr..",
    ".rbbbbbbbbbbbbr.",
    "rbbeeeeeeeeebr.",
    "rbbeeeeeeeeebr.",
    "rbbeeeeeeeeebr.",
    "rbbeeeeeeeeebr.",
    "rbbeeeeeeeeebr.",
    ".rbbbbbbbbbbbr..",
    "..rrssbbbbssrr..",
    "....rrrrrrrr....",
    "................",
], _FOOD_BOWL_CHAR, width=16)

FACILITY_PIXELS_CLOSE["food_bowl_full"] = decode_sprite([
    "....rrrrrrrr....",
    "..rrbbbbbbbbrr..",
    ".rbbffffffffffr.",
    "rbbfffffffffffr.",
    "rbbfffffffffffr.",
    "rbbfffffffffffr.",
    "rbbfffffffffffr.",
    "rbbfffffffffffr.",
    ".rbbbbbbbbbbbr..",
    "..rrssbbbbssrr..",
    "....rrrrrrrr....",
    "................",
], _FOOD_BOWL_CHAR, width=16)

# ---------------------------------------------------------------------------
# WATER BOTTLE (10w × 20h)  —  water surface, glass reflection, drip detail
# ---------------------------------------------------------------------------

_WATER_CHAR = {
    ".": None, "r": "frame", "g": "glass", "w": "water",
    "e": "empty", "c": "cap", "n": "nozzle", "d": "drop",
}

FACILITY_PIXELS_CLOSE["water_bottle"] = decode_sprite([
    "..cccccc..",
    "..cccccc..",
    "rgggggggr.",
    "rgggggggr.",
    "rwwwwwwwr.",
    "rwwwwwwwr.",
    "rwwwwwwwr.",
    "rwwwwwwwr.",
    "rwwwwwwwr.",
    "rwwwwwwwr.",
    "rgggggggr.",
    "rgggggggr.",
    "rgggggggr.",
    "rgggggggr.",
    "rrrrrrrr..",
    "rrrrrrrr..",
    "....nn....",
    "....nn....",
    "....dd....",
    "....dd....",
], _WATER_CHAR, width=10)

FACILITY_PIXELS_CLOSE["water_bottle_empty"] = decode_sprite([
    "..cccccc..",
    "..cccccc..",
    "rgggggggr.",
    "rgggggggr.",
    "reeeeeeeer",
    "reeeeeeeer",
    "reeeeeeeer",
    "reeeeeeeer",
    "reeeeeeeer",
    "reeeeeeeer",
    "reeeeeeeer",
    "reeeeeeeer",
    "rgggggggr.",
    "rgggggggr.",
    "rrrrrrrr..",
    "rrrrrrrr..",
    "....nn....",
    "....nn....",
    "..........",
    "..........",
], _WATER_CHAR, width=10)

FACILITY_PIXELS_CLOSE["water_bottle_full"] = decode_sprite([
    "..cccccc..",
    "..cccccc..",
    "rgggggggr.",
    "rgggggggr.",
    "rwwwwwwwr.",
    "rwwwwwwwr.",
    "rwwwwwwwr.",
    "rwwwwwwwr.",
    "rwwwwwwwr.",
    "rwwwwwwwr.",
    "rwwwwwwwr.",
    "rwwwwwwwr.",
    "rgggggggr.",
    "rgggggggr.",
    "rrrrrrrr..",
    "rrrrrrrr..",
    "....nn....",
    "....nn....",
    "....dd....",
    "....dd....",
], _WATER_CHAR, width=10)

# ---------------------------------------------------------------------------
# HAY RACK (16w × 16h)  —  hay strands, wood slat grain, wisps above
# ---------------------------------------------------------------------------

_HAY_CHAR = {
    ".": None, "r": "frame", "h": "hay", "s": "straw", "e": "empty", "l": "slat",
}

FACILITY_PIXELS_CLOSE["hay_rack"] = decode_sprite([
    "....hshs.shsh...",
    "..hshshs.shssh..",
    ".hsshshshshshsh.",
    ".hsshshshshshsh.",
    "rrllrrrrrrrrlrr.",
    "rrllrrrrrrrrlrr.",
    "rrhshshshshshshr",
    "rrhshshshshshshr",
    "rrhshshshshshshr",
    "rrhshshshshshshr",
    "rrhhhhhhhhhhhhr.",
    "rrhhhhhhhhhhhhr.",
    "rrllhhhhhhhhlrr.",
    "rrllhhhhhhhhlrr.",
    "rrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrr",
], _HAY_CHAR, width=16)

FACILITY_PIXELS_CLOSE["hay_rack_empty"] = decode_sprite([
    "................",
    "................",
    "................",
    "................",
    "rrllrrrrrrrrlrr.",
    "rrllrrrrrrrrlrr.",
    "rreeeeeeeeeeeer.",
    "rreeeeeeeeeeeer.",
    "rreeeeeeeeeeeer.",
    "rreeeeeeeeeeeer.",
    "rreeeeeeeeeeeer.",
    "rreeeeeeeeeeeer.",
    "rrlleeeeeeellrr.",
    "rrlleeeeeeellrr.",
    "rrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrr",
], _HAY_CHAR, width=16)

FACILITY_PIXELS_CLOSE["hay_rack_full"] = decode_sprite([
    "..shshshshshsh..",
    "hshshshshshshsh.",
    "hsshshshshshssh.",
    "hsshshshshshssh.",
    "rrllrrrrrrrrlrr.",
    "rrllrrrrrrrrlrr.",
    "rrhsshshshsshr.",
    "rrhsshshshsshr.",
    "rrshshshshshshr.",
    "rrshshshshshshr.",
    "rrhhhhhhhhhhhhr.",
    "rrhhhhhhhhhhhhr.",
    "rrllhhhhhhhhlrr.",
    "rrllhhhhhhhhlrr.",
    "rrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrr",
], _HAY_CHAR, width=16)

# ---------------------------------------------------------------------------
# HIDEOUT (22w × 16h)  —  roof planks, wood grain walls, deep doorway
# ---------------------------------------------------------------------------

_HIDEOUT_CHAR = {
    ".": None, "r": "frame", "o": "roof", "w": "wall", "d": "door", "p": "plank",
}

FACILITY_PIXELS_CLOSE["hideout"] = decode_sprite([
    "..........oo..........",
    "..........oo..........",
    "........rooor.........",
    "........rooor.........",
    "......rooopoooor......",
    "......rooopoooor......",
    "....rooopooopooor.....",
    "....rooopooopooor.....",
    "rrwwwwwwwwwwwwwwwwwwrr",
    "rrwwwwwwwwwwwwwwwwwwrr",
    "rrwwppwwwwddwwwwppwwrr",
    "rrwwppwwwwddwwwwppwwrr",
    "rrwwwwwwddddddwwwwwwrr",
    "rrwwwwwwddddddwwwwwwrr",
    "rrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrr",
], _HIDEOUT_CHAR, width=22)

# ---------------------------------------------------------------------------
# EXERCISE WHEEL (18w × 16h)  —  circular wheel, spokes, hub, stand
# ---------------------------------------------------------------------------

_WHEEL_CHAR = {
    ".": None, "r": "frame", "w": "wheel", "s": "spoke", "a": "axle", "t": "stand",
}

FACILITY_PIXELS_CLOSE["exercise_wheel"] = decode_sprite([
    "....rrwwwwwwrr....",
    "....rrwwwwwwrr....",
    "..rrwwsswwsswwrr..",
    "..rrwwsswwsswwrr..",
    "rrwwwwwwwaaawwwwrr",
    "rrwwwwwwwaaawwwwrr",
    "..rrwwsswwsswwrr..",
    "..rrwwsswwsswwrr..",
    "....rrwwwwwwrr....",
    "....rrwwwwwwrr....",
    "..ttttrrrrrrttt...",
    "..ttttrrrrrrttt...",
    "..tt......tt......",
    "..tt......tt......",
    "........tt........",
    "........tt........",
], _WHEEL_CHAR, width=18)

# ---------------------------------------------------------------------------
# TUNNEL (18w × 12h)  —  corrugated ridges, depth in openings
# ---------------------------------------------------------------------------

_TUNNEL_CHAR = {
    ".": None, "r": "frame", "t": "tube", "o": "open", "g": "ridge",
}

FACILITY_PIXELS_CLOSE["tunnel"] = decode_sprite([
    "..rrggttttttggrr..",
    "..rrggttttttggrr..",
    "oottttttttttttttoo",
    "oottttttttttttttoo",
    "rrttttggttggttttoo",
    "rrttttggttggttttoo",
    "rrttttggttggttttoo",
    "rrttttggttggttttoo",
    "oottttttttttttttoo",
    "oottttttttttttttoo",
    "..rrggttttttggrr..",
    "..rrggttttttggrr..",
], _TUNNEL_CHAR, width=18)

# ---------------------------------------------------------------------------
# PLAY AREA (20w × 16h)  —  fence posts, grass texture, scattered toys
# ---------------------------------------------------------------------------

_PLAY_CHAR = {
    ".": None, "r": "frame", "f": "fence", "g": "grass",
    "b": "ball", "k": "block", "s": "star",
}

FACILITY_PIXELS_CLOSE["play_area"] = decode_sprite([
    "rrffffffffffffffrr..",
    "rrffffffffffffffrr..",
    "rrgggggggggggggggrr.",
    "rrgggggggggggggggrr.",
    "rrggbbggggssggkkgrr.",
    "rrggbbggggssggkkgrr.",
    "rrgggggggggggggggrr.",
    "rrgggggggggggggggrr.",
    "rrgggggggggggggggrr.",
    "rrgggggggggggggggrr.",
    "rrggkkggssggggbbgrr.",
    "rrggkkggssggggbbgrr.",
    "rrgggggggggggggggrr.",
    "rrgggggggggggggggrr.",
    "rrffffffffffffffrr..",
    "rrffffffffffffffrr..",
], _PLAY_CHAR, width=20)

# ---------------------------------------------------------------------------
# BREEDING DEN (18w × 16h)  —  heart shapes, cushion texture, roof planks
# ---------------------------------------------------------------------------

_BREED_CHAR = {
    ".": None, "r": "frame", "w": "wall", "h": "heart",
    "c": "cushion", "o": "roof",
}

FACILITY_PIXELS_CLOSE["breeding_den"] = decode_sprite([
    "..rroooooooooorr..",
    "..rroooooooooorr..",
    "rrwwwwwwwwwwwwwwrr",
    "rrwwwwwwwwwwwwwwrr",
    "rrwwwwhwwwwhwwwwrr",
    "rrwwwwhhwwhhwwwwrr",
    "rrwwhhhhhhhhhwwwrr",
    "rrwwhhhhhhhhhwwwrr",
    "rrwwwwhhhhhwwwwwrr",
    "rrwwwwwhhhwwwwwwrr",
    "rrwwccwwwhwwccwwrr",
    "rrwwccwwwwwwccwwrr",
    "rrwwccccccccccwwrr",
    "rrwwccccccccccwwrr",
    "..rrrrrrrrrrrrrr..",
    "..rrrrrrrrrrrrrr..",
], _BREED_CHAR, width=18)

# ---------------------------------------------------------------------------
# NURSERY (22w × 16h)  —  rail spindles, mobile detail, blanket folds
# ---------------------------------------------------------------------------

_NURSERY_CHAR = {
    ".": None, "r": "frame", "w": "wall", "s": "star",
    "b": "blanket", "m": "mobile", "l": "rail",
}

FACILITY_PIXELS_CLOSE["nursery"] = decode_sprite([
    "rrllllllllllllllllllrr",
    "rrllllllllllllllllllrr",
    "rrwwwwwwmmwwmmwwwwwwrr",
    "rrwwwwwwmmwwmmwwwwwwrr",
    "rrwwwwsswwwwwwsswwwwrr",
    "rrwwwwsswwwwwwsswwwwrr",
    "rrwwwwwwwwwwwwwwwwwwrr",
    "rrwwwwwwwwwwwwwwwwwwrr",
    "rrwwwwwwwwwwwwwwwwwwrr",
    "rrwwwwwwwwwwwwwwwwwwrr",
    "rrwwbbbbbbbbbbbbbbwwrr",
    "rrwwbbbbbbbbbbbbbbwwrr",
    "rrwwbbbbbbbbbbbbbbwwrr",
    "rrwwbbbbbbbbbbbbbbwwrr",
    "rrllllllllllllllllllrr",
    "rrllllllllllllllllllrr",
], _NURSERY_CHAR, width=22)

# ---------------------------------------------------------------------------
# VEGGIE GARDEN (18w × 16h)  —  vegetable rows, carrot/tomato shapes, leaves
# ---------------------------------------------------------------------------

_VEGGIE_CHAR = {
    ".": None, "r": "frame", "s": "soil", "l": "leaf",
    "v": "veggie", "t": "stem", "c": "carrot",
}

FACILITY_PIXELS_CLOSE["veggie_garden"] = decode_sprite([
    "rrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrr",
    "rrssllssttsslssrr.",
    "rrssllssttsslssrr.",
    "rrttssllssllssttri",
    "rrttssllssllssttri",
    "rrllccllvvllccllrr",
    "rrllccllvvllccllrr",
    "rrssttssttssttssrr",
    "rrssttssttssttssrr",
    "rrllssccssccssllrr",
    "rrllssccssccssllrr",
    "rrssllssllssllssrr",
    "rrssllssllssllssrr",
    "rrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrr",
], _VEGGIE_CHAR, width=18)

# ---------------------------------------------------------------------------
# GROOMING STATION (18w × 16h)  —  oval mirror, brush bristles, stand
# ---------------------------------------------------------------------------

_GROOM_CHAR = {
    ".": None, "r": "frame", "m": "mirror", "s": "shine",
    "b": "brush", "a": "base", "t": "stand",
}

FACILITY_PIXELS_CLOSE["grooming_station"] = decode_sprite([
    "....rrrrrrrrrr....",
    "....rrrrrrrrrr....",
    "..rrmmmmssmmmrr...",
    "..rrmmmmssmmmrr...",
    "..rrmmmmmmmmmmrr..",
    "..rrmmmmmmmmmmrr..",
    "....rrrrrrrrrr....",
    "....rrrrrrrrrr....",
    "........tt........",
    "........tt........",
    "..rraaaaaaaaarrr..",
    "..rraaaaaaaaarrr..",
    "..rrbbaaaaaabrrr..",
    "..rrbbaaaaaabrrr..",
    "..rrrrrrrrrrrrrr..",
    "..rrrrrrrrrrrrrr..",
], _GROOM_CHAR, width=18)

# ---------------------------------------------------------------------------
# GENETICS LAB (22w × 16h)  —  DNA helix spiral, flask with bubbles, glow
# ---------------------------------------------------------------------------

_LAB_CHAR = {
    ".": None, "r": "frame", "b": "base", "f": "flask",
    "l": "liquid", "d": "dna", "g": "glow",
}

FACILITY_PIXELS_CLOSE["genetics_lab"] = decode_sprite([
    "rrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrr",
    "rrbbbbffbbddbbffbbbbrr",
    "rrbbbbffbbddbbffbbbbrr",
    "rrbbffffbbddbbffffbbrr",
    "rrbbffffbbddbbffffbbrr",
    "rrbbffllbbggbbllffbbrr",
    "rrbbffllbbggbbllffbbrr",
    "rrbbffllddddddllffbbrr",
    "rrbbffllddddddllffbbrr",
    "rrbbbbbbbbddbbbbbbbirr",
    "rrbbbbbbbbddbbbbbbbirr",
    "rrbbggbbbbddbbbbggbbrr",
    "rrbbggbbbbddbbbbggbbrr",
    "rrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrr",
], _LAB_CHAR, width=22)

# fmt: on
