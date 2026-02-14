"""Procedural pig portraits — face generation and scene compositing."""

import copy
import hashlib
import random as _random

from big_pig_farm.data.sprite_engine import PixelGrid, T


# ---------------------------------------------------------------------------
# Procedural pig portraits  (32 x 24 pixels -> 32 x 12 half-block chars)
# ---------------------------------------------------------------------------

# The 32x24 face template: a front-facing guinea pig head.
# Guinea pigs are WIDER than tall with puffy cheeks and fluffy fur.
# Key features that make it look like a guinea pig, not a potato:
#   - Irregular silhouette with fur tufts breaking the outline
#   - Prominent rounded ears on the sides with inner-ear detail
#   - Cartoonish eyes (3x3 white sclera with dark pupil center)
#   - Small distinct nose with nostrils + little mouth with teeth
#   - Fluffy cheek poufs that bulge outward
#   - Wisps of fur on top of head (rosette) using  T key
# Uses palette keys directly — pattern/intensity functions mutate them.
# fmt: off
_FACE_TEMPLATE: PixelGrid = [
    #  0      1      2      3      4      5      6      7      8      9     10     11     12     13     14     15     16     17     18     19     20     21     22     23     24     25     26     27     28     29     30     31
    [ T,     T,     T,     T,     T,     T,     T,     T, T,     T, T,     T,    "dark","dark","dark","dark","dark","dark","dark","dark", T,     T,     T, T,     T, T,     T,     T,     T,     T,     T,     T    ],  # 0  rosette tufts
    [ T,     T,     T,     T,     T,     T,     T, T,    "dark","dark","dark","dark","fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark","dark","dark","dark", T,     T, T,     T,     T,     T,     T,     T    ],  # 1  crown + tufts
    [ T,     T,     T,     T,     T,     T,    "dark","dark","fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark","dark", T,     T,     T,     T,     T,     T    ],  # 2  upper head
    [ T,     T,     T,     T,     T,    "dark","fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark", T,     T,     T,     T,     T    ],  # 3  forehead
    [ T,     T,     T,    "dark","ear", "ear","dark", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark","ear", "ear","dark", T,     T,     T    ],  # 4  ears start
    [ T,     T,    "dark","ear", "ear", "ear","dark", "fur", "fur","dark","dark","dark","dark","dark","fur", "fur", "fur", "fur","dark","dark","dark","dark","dark","fur", "fur","dark","ear", "ear", "ear","dark", T,     T    ],  # 5  above eyes (outline top)
    [ T,    "dark","ear", "ear", "ear","dark","fur",  "fur","dark", "eye", "eye","pupil","dark", "fur", "fur", "fur", "fur", "fur","dark", "eye", "eye","pupil","dark", "fur", "fur", "fur","dark","ear", "ear", "ear","dark", T    ],  # 6  eyes top (gleam + pupil)
    [ T,    "dark","ear", "ear","dark","dark","fur",  "fur","dark", "eye","pupil","pupil","dark", "fur", "fur", "fur", "fur", "fur","dark", "eye","pupil","pupil","dark", "fur", "fur", "fur","dark","dark","ear", "ear","dark", T    ],  # 7  eyes mid (pupil 2x2 lower)
    [ T,   "dark","dark","dark", T,   "dark","fur",  "fur","dark", "eye", "eye", "eye","dark", "fur", "fur", "fur", "fur", "fur","dark", "eye", "eye", "eye","dark", "fur", "fur", "fur","dark", T,   "dark","dark","dark", T    ],  # 8  eyes bottom (sclera + outline)
    [ T,     T,     T,     T,     T,   "dark","fur",  "fur", "fur","dark","dark","dark","dark", "fur", "fur", "fur", "fur", "fur", "fur","dark","dark","dark","dark", "fur", "fur", "fur","dark", T,     T,     T,     T,     T    ],  # 9  below eyes (outline bottom)
    [ T, T,     T,    "dark","dark","fur", "fur","blush","blush","fur", "fur", "fur", "fur", "fur", "fur","nose","nose","fur", "fur", "fur", "fur", "fur", "fur","blush","blush","fur", "fur","dark","dark", T,     T,     T],  # 10 cheeks + blush + nose top
    [ T,     T,    "dark","fur","dark","fur", "fur",  "fur", "fur", "fur", "fur", "fur", "fur", "fur","nose","nose","nose","nose","fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark","fur","dark", T,     T    ],  # 11 nose pad + cheek tufts
    [ T,    "dark","fur", "fur","dark","fur", "fur",  "fur", "fur", "fur", "fur", "fur", "fur","fur","dark","nose","nose","dark","fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark","fur", "fur","dark", T    ],  # 12 nostrils
    ["dark","fur", "fur","dark","dark","fur", "fur",  "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark","dark","fur", "fur","dark"],  # 13 below nose + cheek tufts
    ["dark","fur", "fur", "fur","dark","fur", "fur",  "fur", "fur", "fur", "fur", "fur", "fur","dark","dark","tooth","tooth","dark","dark","fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark","fur", "fur", "fur","dark"],  # 14 mouth + teeth + cheek tufts
    ["dark","fur",  T,     T,    "dark","fur", "fur",  "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark","dark","dark","dark","fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark", T,     T,    "fur","dark"],  # 15 lower lip + tuft bridge
    ["dark","fur","dark","dark","fur",  "fur",  "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur","dark","dark","fur","dark", T    ],  # 16 lower cheeks + small tufts
    ["dark","dark","fur",  "fur", "dark","dark","fur", "fur", "fur", "fur", "fur", "fur", "fur","dark","dark","dark","dark","fur", "fur", "fur", "fur", "fur", "fur", "fur","dark","dark", "fur", "fur", "fur","dark","dark","dark"],  # 17 chin outline + body starts
    ["dark","fur",  "fur",  "fur", "fur", "fur","dark","dark","dark","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","dark","dark","dark", "fur", "fur", "fur", "fur", "fur","dark"],  # 18 chin curves into body
    ["fur",  "fur",  "fur", "fur", "fur", "fur", "fur", "fur","dark","dark","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","dark","dark","fur", "fur", "fur", "fur", "fur", "fur", "fur", "fur"],  # 19 chin bottom merges
    ["fur",  "fur",  "fur", "fur", "fur", "fur", "belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","fur", "fur", "fur", "fur", "fur", "fur"],  # 20 body extends past edges
    ["fur",  "fur",  "fur", "fur", "fur", "belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","fur", "fur", "fur", "fur", "fur"],  # 21 body continues off-frame
]
# fmt: on

# Regions: sets of (row, col) coordinates for pattern/intensity targeting
_FUR_PIXELS: set[tuple[int, int]] = set()
_EAR_PIXELS: set[tuple[int, int]] = set()
_NOSE_PIXELS: set[tuple[int, int]] = set()
_FOREHEAD_PIXELS: set[tuple[int, int]] = set()  # rows 0-7, inner area
_CHIN_PIXELS: set[tuple[int, int]] = set()       # rows 16-23, inner area

for _r, _row in enumerate(_FACE_TEMPLATE):
    for _c, _val in enumerate(_row):
        if _val == "ear":
            _EAR_PIXELS.add((_r, _c))
        elif _val == "fur":
            _FUR_PIXELS.add((_r, _c))
            if _r <= 7:
                _FOREHEAD_PIXELS.add((_r, _c))
            if _r >= 16:
                _CHIN_PIXELS.add((_r, _c))
        elif _val == "nose":
            _NOSE_PIXELS.add((_r, _c))

# Inner fur: fur pixels where ALL 4 neighbors are also fur/nose/eye/pupil
# (not adjacent to outline, ears, tufts, or transparency).
# Used for dalmatian spots and roan scatter to keep patterns inside the face.
_INNER_KEYS = {"fur", "nose", "eye", "pupil"}
_INNER_FUR_PIXELS: set[tuple[int, int]] = set()
for _r, _c in _FUR_PIXELS:
    _all_inner = True
    for _dr, _dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        _nr, _nc = _r + _dr, _c + _dc
        _nval = _FACE_TEMPLATE[_nr][_nc] if 0 <= _nr < len(_FACE_TEMPLATE) and 0 <= _nc < len(_FACE_TEMPLATE[0]) else None
        if _nval not in _INNER_KEYS:
            _all_inner = False
            break
    if _all_inner:
        _INNER_FUR_PIXELS.add((_r, _c))


def _seeded_rng(pig_id: str) -> _random.Random:
    """Create a deterministic RNG from a pig's UUID string."""
    seed = int(hashlib.md5(pig_id.encode()).hexdigest()[:8], 16)
    return _random.Random(seed)


def _apply_dalmatian_spots(grid: PixelGrid, pig_id: str) -> None:
    """Scatter white spots across inner fur pixels — seeded by pig ID."""
    rng = _seeded_rng(pig_id + "_dalmatian")
    fur_list = sorted(_INNER_FUR_PIXELS)  # deterministic order, interior only
    # Pick ~25-35% of inner fur pixels as spot clusters
    spot_centers = rng.sample(fur_list, k=max(1, len(fur_list) // 4))
    spotted: set[tuple[int, int]] = set()

    for r, c in spot_centers:
        spotted.add((r, c))
        # Expand each center to a small cluster (1-2 neighbors)
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if (nr, nc) in _INNER_FUR_PIXELS and rng.random() < 0.5:
                spotted.add((nr, nc))

    for r, c in spotted:
        grid[r][c] = "white"


def _apply_dutch_markings(grid: PixelGrid) -> None:
    """Apply Dutch pattern: white blaze on forehead + white chin."""
    # White blaze: center columns of forehead
    for r, c in _FOREHEAD_PIXELS:
        if 12 <= c <= 19:  # center area
            grid[r][c] = "white"

    # White chin
    for r, c in _CHIN_PIXELS:
        grid[r][c] = "white"


def _apply_himalayan(grid: PixelGrid) -> None:
    """Himalayan: lighten body fur to near-white, keep ears/nose colored."""
    for r, c in _FUR_PIXELS:
        if (r, c) not in _EAR_PIXELS:
            grid[r][c] = "belly"  # use belly (lighter) color for body


def _apply_chinchilla(grid: PixelGrid) -> None:
    """Chinchilla: silver tint — replace some inner fur with white mix."""
    for r, c in _INNER_FUR_PIXELS:
        # Alternate pixels to create a silver/ticked effect
        if (r + c) % 3 == 0:
            grid[r][c] = "white"


def _apply_roan(grid: PixelGrid, pig_id: str) -> None:
    """Roan: scatter white hairs through inner fur, seeded by pig ID."""
    rng = _seeded_rng(pig_id + "_roan")
    fur_list = sorted(_INNER_FUR_PIXELS)

    for r, c in fur_list:
        if grid[r][c] not in ("white", "eye", "pupil", "dark",  T, "tooth", T):
            if rng.random() < 0.3:  # 30% of fur pixels turn white
                grid[r][c] = "white"


def generate_portrait(
    base_color_name: str,
    pattern: str,
    intensity: str,
    roan: str,
    pig_id: str,
) -> PixelGrid:
    """Generate a 32x24 pixel face portrait from phenotype traits.

    Args:
        base_color_name: "BLACK", "CHOCOLATE", "GOLDEN", or "CREAM"
        pattern: "solid", "dutch", or "dalmatian"
        intensity: "full", "chinchilla", or "himalayan"
        roan: "none" or "roan"
        pig_id: UUID string for deterministic randomness

    Returns:
        32x24 pixel grid with palette keys. Use with convert_pixels() + PALETTES.
    """
    grid = copy.deepcopy(_FACE_TEMPLATE)

    # 1. Apply pattern (modifies fur pixels to "white")
    if pattern == "dalmatian":
        _apply_dalmatian_spots(grid, pig_id)
    elif pattern == "dutch":
        _apply_dutch_markings(grid)

    # 2. Apply intensity (lightens/modifies fur pixels)
    if intensity == "himalayan":
        _apply_himalayan(grid)
    elif intensity == "chinchilla":
        _apply_chinchilla(grid)

    # 3. Apply roan (scatters white into remaining fur)
    if roan == "roan":
        _apply_roan(grid, pig_id)

    return grid


# ---------------------------------------------------------------------------
# Scene background for pig portraits
# ---------------------------------------------------------------------------

SCENE_BG_COLORS: dict[str, str] = {
    "sky_light": "#87ceeb",
    "sky_dark": "#6bb3d9",
    "grass_light": "#6abf4b",
    "grass": "#4a9e2f",
    "grass_dark": "#3b8125",
}


def generate_background(width: int, height: int) -> PixelGrid:
    """Build a sky + grass background grid of literal hex color strings.

    Rows 0-9: light sky, 10-15: darker sky, 16-17: light grass (horizon),
    18+: grass with occasional dark grass variation.
    """
    grid: PixelGrid = []
    for y in range(height):
        if y < 10:
            color = SCENE_BG_COLORS["sky_light"]
        elif y < 16:
            color = SCENE_BG_COLORS["sky_dark"]
        elif y < 18:
            color = SCENE_BG_COLORS["grass_light"]
        else:
            color = SCENE_BG_COLORS["grass_dark" if y % 2 == 0 else "grass"]
        grid.append([color] * width)
    return grid


def generate_portrait_with_scene(
    base_color_name: str,
    pattern: str,
    intensity: str,
    roan: str,
    pig_id: str,
) -> PixelGrid:
    """Generate a portrait composited over a sky + grass background."""
    portrait = generate_portrait(base_color_name, pattern, intensity, roan, pig_id)
    p_height = len(portrait)
    p_width = max(len(row) for row in portrait)

    bg = generate_background(p_width, p_height)

    # Composite portrait over background — portrait pixels replace bg where non-None
    for y in range(p_height):
        for x in range(len(portrait[y])):
            if portrait[y][x] is not None:
                bg[y][x] = portrait[y][x]

    return bg
