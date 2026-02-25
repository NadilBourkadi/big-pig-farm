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

# ---------------------------------------------------------------------------
# FEAST TABLE (28w × 28h)  —  large communal banquet table with plates
# ---------------------------------------------------------------------------

_FEAST_CHAR = {
    ".": None, "r": "frame", "t": "table", "p": "plank",
    "f": "food", "a": "plate", "l": "leg",
}

FACILITY_PIXELS_CLOSE["feast_table"] = decode_sprite([
    "rrpppppppppppppppppppppppppp",
    "rrpppppppppppppppppppppppppp",
    "rrttttaaffaaffaaffaaffaattrr",
    "rrttttaaffaaffaaffaaffaattrr",
    "rrttaaffaaffaaffaaffaaffaarr",
    "rrttaaffaaffaaffaaffaaffaarr",
    "rrttffaaffaaffaaffaaffaattrr",
    "rrttffaaffaaffaaffaaffaattrr",
    "rrttaaffaaffaaffaaffaaffaarr",
    "rrttaaffaaffaaffaaffaaffaarr",
    "rrttttaaffaaffaaffaaffaattrr",
    "rrttttaaffaaffaaffaaffaattrr",
    "rrpppppppppppppppppppppppppp",
    "rrpppppppppppppppppppppppppp",
    "..llll......rrrrrr......llll",
    "..llll......rrrrrr......llll",
    "..llll......rrrrrr......llll",
    "..llll......rrrrrr......llll",
    "..llll....................ll",
    "..llll....................ll",
    "..llll....................ll",
    "..llll....................ll",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
], _FEAST_CHAR, width=28)

FACILITY_PIXELS_CLOSE["feast_table_empty"] = decode_sprite([
    "rrpppppppppppppppppppppppppp",
    "rrpppppppppppppppppppppppppp",
    "rrttttaattaattaattaattaattrr",
    "rrttttaattaattaattaattaattrr",
    "rrttaattaattaattaattaattaarr",
    "rrttaattaattaattaattaattaarr",
    "rrttttaattaattaattaattaattrr",
    "rrttttaattaattaattaattaattrr",
    "rrttaattaattaattaattaattaarr",
    "rrttaattaattaattaattaattaarr",
    "rrttttaattaattaattaattaattrr",
    "rrttttaattaattaattaattaattrr",
    "rrpppppppppppppppppppppppppp",
    "rrpppppppppppppppppppppppppp",
    "..llll......rrrrrr......llll",
    "..llll......rrrrrr......llll",
    "..llll......rrrrrr......llll",
    "..llll......rrrrrr......llll",
    "..llll....................ll",
    "..llll....................ll",
    "..llll....................ll",
    "..llll....................ll",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
], _FEAST_CHAR, width=28)

FACILITY_PIXELS_CLOSE["feast_table_full"] = decode_sprite([
    "rrpppppppppppppppppppppppppp",
    "rrpppppppppppppppppppppppppp",
    "rrttffffffffffffffffffttttrr",
    "rrttffffffffffffffffffttttrr",
    "rrttffffffffffffffffffttttrr",
    "rrttffffffffffffffffffttttrr",
    "rrttffffffffffffffffffttttrr",
    "rrttffffffffffffffffffttttrr",
    "rrttffffffffffffffffffttttrr",
    "rrttffffffffffffffffffttttrr",
    "rrttffffffffffffffffffttttrr",
    "rrttffffffffffffffffffttttrr",
    "rrpppppppppppppppppppppppppp",
    "rrpppppppppppppppppppppppppp",
    "..llll......rrrrrr......llll",
    "..llll......rrrrrr......llll",
    "..llll......rrrrrr......llll",
    "..llll......rrrrrr......llll",
    "..llll....................ll",
    "..llll....................ll",
    "..llll....................ll",
    "..llll....................ll",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
], _FEAST_CHAR, width=28)

# ---------------------------------------------------------------------------
# CAMPFIRE (28w × 28h)  —  large stone ring with crackling fire
# ---------------------------------------------------------------------------

_CAMP_CHAR = {
    ".": None, "r": "frame", "s": "stone", "f": "fire",
    "m": "flame", "e": "ember", "l": "log", "a": "ash",
}

FACILITY_PIXELS_CLOSE["campfire"] = decode_sprite([
    "........mmmmmmmm............",
    "........mmmmmmmm............",
    "......mmmmmmmmmmmm..........",
    "......mmmmmmmmmmmm..........",
    "....mmmmffffffmmmm..........",
    "....mmmmffffffmmmm..........",
    "....mmffffffffffffffmm......",
    "....mmffffffffffffffmm......",
    "..ssffffeefffeeeffffffff....",
    "..ssffffeefffeeeffffffff....",
    "ssssffffffeeeeeefffffffss...",
    "ssssffffffeeeeeefffffffss...",
    "sslllllleeeeeeeeellllllss...",
    "sslllllleeeeeeeeellllllss...",
    "ssllllllaaaaaaaaallllllss...",
    "ssllllllaaaaaaaaallllllss...",
    "rrssssllllaaaallllssssrr....",
    "rrssssllllaaaallllssssrr....",
    "..rrssssssssssssssssrr......",
    "..rrssssssssssssssssrr......",
    "....rrrrrrrrrrrrrrrr........",
    "....rrrrrrrrrrrrrrrr........",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
], _CAMP_CHAR, width=28)

# ---------------------------------------------------------------------------
# THERAPY GARDEN (28w × 28h)  —  lush flower garden with winding path
# ---------------------------------------------------------------------------

_THERAPY_CHAR = {
    ".": None, "r": "frame", "g": "grass", "f": "flower",
    "p": "petal", "l": "leaf", "t": "path", "w": "water",
}

FACILITY_PIXELS_CLOSE["therapy_garden"] = decode_sprite([
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrggggffggllggllggppggggllrr",
    "rrggggffggllggllggppggggllrr",
    "rrggffggppggffggppggffggpprr",
    "rrggffggppggffggppggffggpprr",
    "rrllggppggttttttttggffgglgrr",
    "rrllggppggttttttttggffgglgrr",
    "rrggppggttttttttttttggppffrr",
    "rrggppggttttttttttttggppffrr",
    "rrffggtttttwwwwwwttttggffrr.",
    "rrffggtttttwwwwwwttttggffrr.",
    "rrgglltttwwwwwwwwwwtttllggrr",
    "rrgglltttwwwwwwwwwwtttllggrr",
    "rrppggtttwwwwwwwwwwtttggpprr",
    "rrppggtttwwwwwwwwwwtttggpprr",
    "rrggfftttttwwwwwwttttffggrr.",
    "rrggfftttttwwwwwwttttffggrr.",
    "rrllggppttttttttttttggllpprr",
    "rrllggppttttttttttttggllpprr",
    "rrggppggllttttttttppggffggrr",
    "rrggppggllttttttttppggffggrr",
    "rrffggllggppggffggllggppffrr",
    "rrffggllggppggffggllggppffrr",
    "rrggllggffggppggllggffggllrr",
    "rrggllggffggppggllggffggllrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrr",
], _THERAPY_CHAR, width=28)

# ---------------------------------------------------------------------------
# HOT SPRING (36w × 36h)  —  large stone-rimmed pool, steam, rocky edge
# ---------------------------------------------------------------------------

_SPRING_CHAR = {
    ".": None, "r": "frame", "s": "stone", "w": "water",
    "t": "steam", "p": "pool", "k": "rock",
}

FACILITY_PIXELS_CLOSE["hot_spring"] = decode_sprite([
    "....tt....tt....tt....tt............",
    "....tt....tt....tt....tt............",
    "......tt....tt....tt....tt..........",
    "......tt....tt....tt....tt..........",
    "........tt....tt....tt....tt........",
    "........tt....tt....tt....tt........",
    "....rrssssssssssssssssssssssssrr....",
    "....rrssssssssssssssssssssssssrr....",
    "..rrssppppppppppppppppppppppppssrr..",
    "..rrssppppppppppppppppppppppppssrr..",
    "rrssppppppwwwwwwwwwwwwwwppppppppssrr",
    "rrssppppppwwwwwwwwwwwwwwppppppppssrr",
    "rrssppppwwwwwwwwwwwwwwwwwwppppppssrr",
    "rrssppppwwwwwwwwwwwwwwwwwwppppppssrr",
    "rrssppwwwwwwppppppppwwwwwwwwppppssrr",
    "rrssppwwwwwwppppppppwwwwwwwwppppssrr",
    "rrsswwwwwwppppppppppppwwwwwwwwwwssrr",
    "rrsswwwwwwppppppppppppwwwwwwwwwwssrr",
    "rrsswwwwwwppppppppppppwwwwwwwwwwssrr",
    "rrsswwwwwwppppppppppppwwwwwwwwwwssrr",
    "rrssppwwwwwwppppppppwwwwwwwwppppssrr",
    "rrssppwwwwwwppppppppwwwwwwwwppppssrr",
    "rrssppppwwwwwwwwwwwwwwwwwwppppppssrr",
    "rrssppppwwwwwwwwwwwwwwwwwwppppppssrr",
    "rrssppppppwwwwwwwwwwwwwwppppppppssrr",
    "rrssppppppwwwwwwwwwwwwwwppppppppssrr",
    "..rrssppppppppppppppppppppppppssrr..",
    "..rrssppppppppppppppppppppppppssrr..",
    "....rrssssssssssssssssssssssssrr....",
    "....rrssssssssssssssssssssssssrr....",
    "......rrrrrrkkkk....kkkkrrrrrr......",
    "......rrrrrrkkkk....kkkkrrrrrr......",
    "....................................",
    "....................................",
    "....................................",
    "....................................",
], _SPRING_CHAR, width=36)

# ---------------------------------------------------------------------------
# STAGE (36w × 36h)  —  large curtained stage with spotlight
# ---------------------------------------------------------------------------

_STAGE_CHAR = {
    ".": None, "r": "frame", "f": "floor", "c": "curtain",
    "l": "light", "s": "star", "b": "base",
}

FACILITY_PIXELS_CLOSE["stage"] = decode_sprite([
    "ccccccllccccccccssccccccllcccccccccc",
    "ccccccllccccccccssccccccllcccccccccc",
    "cccccccccccccccccccccccccccccccccccc",
    "cccccccccccccccccccccccccccccccccccc",
    "cccc............................cccc",
    "cccc............................cccc",
    "cccc............................cccc",
    "cccc............................cccc",
    "cccc............................cccc",
    "cccc............................cccc",
    "cccc..........llll..........cccc....",
    "cccc..........llll..........cccc....",
    "cccc............................cccc",
    "cccc............................cccc",
    "cccc............................cccc",
    "cccc............................cccc",
    "cccc............................cccc",
    "cccc............................cccc",
    "cccc............................cccc",
    "cccc............................cccc",
    "rrrrrrffffffffffffffffffffffrrrrrrrr",
    "rrrrrrffffffffffffffffffffffrrrrrrrr",
    "rrffffffffffffffffffffffffffffffrrrr",
    "rrffffffffffffffffffffffffffffffrrrr",
    "rrffffffffffffffffffffffffffffffrrrr",
    "rrffffffffffffffffffffffffffffffrrrr",
    "..bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb..",
    "..bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb..",
    "..bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb..",
    "..bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb..",
    "....bbbb......bbbb......bbbb.......",
    "....bbbb......bbbb......bbbb.......",
    "....................................",
    "....................................",
    "....................................",
    "....................................",
], _STAGE_CHAR, width=36)

# fmt: on
