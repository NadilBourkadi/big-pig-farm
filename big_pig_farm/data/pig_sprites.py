"""Pig pixel sprite data — all zoom levels and animation frames.

Normal-zoom adults are 14w x 8h pixels (14 x 4 half-block chars).
Normal-zoom babies are 8w x 6h pixels.
Far-zoom adults are 7w x 6h pixels, far-zoom babies are 5w x 4h pixels.

Animated states use 1-indexed suffixes: walking_right_1 (frame 1),
walking_right_2 (frame 2).  Non-animated states (idle, sad) use bare keys.
"""

from big_pig_farm.data.sprite_engine import T

# Palette keys used:  fur, dark, belly, eye, nose, ear, paw, T(ransparent)

# fmt: off

# --- Adult sprites (14w x 8h pixels) ---

PIG_PIXELS_ADULT = {
    "idle_right": [
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark","ear","dark", T,   T  ],
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","fur","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","eye","eye","pupil","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","eye","pupil","pupil","nose","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "idle_left": [
        [ T,   T,  "dark","ear","dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,  "dark","fur","fur","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","pupil","eye","eye","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","nose","pupil","pupil","eye","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "walking_right_1": [
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark","ear","dark", T,   T  ],
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","fur","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","eye","eye","pupil","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","eye","pupil","pupil","nose","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,  "paw", T,   T,   T,   T,   T,   T,   T,   T,  "paw", T,   T  ],
    ],
    "walking_left_1": [
        [ T,   T,  "dark","ear","dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,  "dark","fur","fur","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","pupil","eye","eye","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","nose","pupil","pupil","eye","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,  "paw", T,   T,   T,   T,   T,   T,   T,   T,  "paw", T,   T  ],
    ],
    "eating_right_1": [
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark","ear","dark", T,   T  ],
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","fur","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","dark","dark","fur","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","nose","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "eating_left_1": [
        [ T,   T,  "dark","ear","dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,  "dark","fur","fur","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","fur","dark","dark","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","nose","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "sleeping_right_1": [
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark","ear","dark", T,   T  ],
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","fur","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","dark","dark","fur","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "sleeping_left_1": [
        [ T,   T,  "dark","ear","dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,  "dark","fur","fur","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","fur","dark","dark","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "happy_right_1": [
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark","ear","dark", T,   T  ],
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","fur","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","eye","eye","pupil","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","eye","pupil","pupil","nose","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "happy_left_1": [
        [ T,   T,  "dark","ear","dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,  "dark","fur","fur","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","pupil","eye","eye","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","nose","pupil","pupil","eye","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "sad_right": [
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark","ear","dark", T,   T  ],
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","fur","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","eye","eye","pupil","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","eye","pupil","pupil","nose","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "sad_left": [
        [ T,   T,  "dark","ear","dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,  "dark","fur","fur","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","pupil","eye","eye","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","nose","pupil","pupil","eye","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    # --- Frame 2 variants (animation alternates) ---
    # Walking: body bobs down 1px + leans forward + ear flattens (rocking waddle)
    # Frame 1 = up stride (centered, paws spread), frame 2 = down stride (forward lean, paws tucked)
    "walking_right_2": [
        [ T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark", T,  "dark", T,   T  ],
        [ T,   T,   T,   T,  "dark","dark","dark","dark","fur","fur","ear","fur","fur","dark"],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","eye","eye","pupil","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","eye","pupil","pupil","nose","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,   T,  "dark","fur","fur","fur","fur","fur","fur","fur","belly","belly","dark", T  ],
        [ T,   T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T  ],
    ],
    "walking_left_2": [
        [ T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,   T,  "dark", T,  "dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        ["dark","fur","fur","ear","fur","fur","dark","dark","dark","dark", T,   T,   T,   T  ],
        ["dark","fur","pupil","eye","eye","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","nose","pupil","pupil","eye","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        [ T,  "dark","belly","belly","fur","fur","fur","fur","fur","fur","fur","dark", T,   T  ],
        [ T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T,   T  ],
    ],
    # Walking frame 3: body centred (same as frame 1 height), paws closer together, slight width shift
    "walking_right_3": [
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark","ear","dark", T,   T  ],
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","fur","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","eye","eye","pupil","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","eye","pupil","pupil","nose","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,   T,  "paw", T,   T,   T,   T,  "paw", T,   T,   T,   T  ],
    ],
    "walking_left_3": [
        [ T,   T,  "dark","ear","dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,  "dark","fur","fur","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","pupil","eye","eye","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","nose","pupil","pupil","eye","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,   T,  "paw", T,   T,   T,   T,  "paw", T,   T,   T,   T  ],
    ],
    # Eating: ear flattens + whole face dips (closed eyes shift down 1 row) + nose dips
    "eating_right_2": [
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark", T,  "dark", T,   T  ],
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","ear","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","dark","dark","fur","fur","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","nose","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "eating_left_2": [
        [ T,   T,  "dark", T,  "dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,  "dark","fur","ear","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","fur","dark","dark","fur","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","nose","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    # Happy (playing): hop up 1px + ear merges into head + paws spread (jumping pose)
    "happy_right_2": [
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","ear","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","eye","eye","pupil","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","eye","pupil","pupil","nose","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,  "paw", T,   T,   T,   T,   T,   T,   T,   T,  "paw", T,   T  ],
        [ T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T  ],
    ],
    "happy_left_2": [
        [ T,  "dark","fur","ear","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","pupil","eye","eye","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","nose","pupil","pupil","eye","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","dark", T  ],
        [ T,   T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","dark", T,   T  ],
        [ T,   T,  "paw", T,   T,   T,   T,   T,   T,   T,   T,  "paw", T,   T  ],
        [ T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T,   T  ],
    ],
    # Sleeping: belly + underside expand outward on both sides (visible body puffing)
    "sleeping_right_2": [
        [ T,   T,   T,   T,   T,   T,   T,   T,  "dark","dark","ear","dark", T,   T  ],
        [ T,   T,   T,  "dark","dark","dark","dark","dark","fur","fur","fur","fur","dark", T  ],
        [ T,   T,  "dark","dark","fur","fur","fur","fur","fur","dark","dark","fur","fur","dark"],
        [ T,  "dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        ["dark","belly","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","belly","dark"],
        [ T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","dark", T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
    "sleeping_left_2": [
        [ T,   T,  "dark","ear","dark","dark", T,   T,   T,   T,   T,   T,   T,   T  ],
        [ T,  "dark","fur","fur","fur","fur","dark","dark","dark","dark","dark", T,   T,   T  ],
        ["dark","fur","fur","dark","dark","fur","fur","fur","fur","fur","dark","dark", T,   T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","fur","dark"],
        ["dark","belly","belly","fur","fur","fur","fur","fur","fur","fur","fur","belly","belly","dark"],
        [ T,  "dark","belly","belly","belly","belly","belly","belly","belly","belly","belly","belly","dark", T  ],
        [ T,   T,   T,  "paw", T,   T,   T,   T,   T,   T,  "paw", T,   T,   T  ],
    ],
}

# --- Baby sprites (8w x 6h pixels) ---

PIG_PIXELS_BABY = {
    "idle_right": [
        [ T,   T,   T,   T,  "dark","ear","dark", T  ],
        [ T,  "dark","dark","dark","fur","fur","fur","dark"],
        [ T,  "dark","fur","fur","eye","pupil","fur","dark"],
        ["dark","belly","fur","fur","eye","eye","nose","dark"],
        [ T,  "dark","belly","belly","belly","belly","dark", T  ],
        [ T,   T,  "paw", T,   T,  "paw", T,   T  ],
    ],
    "idle_left": [
        [ T,  "dark","ear","dark", T,   T,   T,   T  ],
        ["dark","fur","fur","fur","dark","dark","dark", T  ],
        ["dark","fur","pupil","eye","fur","fur","dark", T  ],
        ["dark","nose","eye","eye","fur","fur","belly","dark"],
        [ T,  "dark","belly","belly","belly","belly","dark", T  ],
        [ T,   T,  "paw", T,   T,  "paw", T,   T  ],
    ],
    "walking_right_1": [
        [ T,   T,   T,   T,  "dark","ear","dark", T  ],
        [ T,  "dark","dark","dark","fur","fur","fur","dark"],
        [ T,  "dark","fur","fur","eye","pupil","fur","dark"],
        ["dark","belly","fur","fur","eye","eye","nose","dark"],
        [ T,  "dark","belly","belly","belly","belly","dark", T  ],
        [ T,  "paw", T,   T,   T,   T,  "paw", T  ],
    ],
    "walking_left_1": [
        [ T,  "dark","ear","dark", T,   T,   T,   T  ],
        ["dark","fur","fur","fur","dark","dark","dark", T  ],
        ["dark","fur","pupil","eye","fur","fur","dark", T  ],
        ["dark","nose","eye","eye","fur","fur","belly","dark"],
        [ T,  "dark","belly","belly","belly","belly","dark", T  ],
        [ T,  "paw", T,   T,   T,   T,  "paw", T  ],
    ],
    "sleeping_right_1": [
        [ T,   T,   T,   T,  "dark","ear","dark", T  ],
        [ T,  "dark","dark","dark","fur","fur","fur","dark"],
        [ T,  "dark","fur","fur","dark","dark","fur","dark"],
        ["dark","belly","fur","fur","fur","fur","fur","dark"],
        [ T,  "dark","belly","belly","belly","belly","dark", T  ],
        [ T,   T,  "paw", T,   T,  "paw", T,   T  ],
    ],
    "sleeping_left_1": [
        [ T,  "dark","ear","dark", T,   T,   T,   T  ],
        ["dark","fur","fur","fur","dark","dark","dark", T  ],
        ["dark","fur","dark","dark","fur","fur","dark", T  ],
        ["dark","fur","fur","fur","fur","fur","belly","dark"],
        [ T,  "dark","belly","belly","belly","belly","dark", T  ],
        [ T,   T,  "paw", T,   T,  "paw", T,   T  ],
    ],
    # Walking frame 3: body centred, paws closer together (weight-shift pose)
    "walking_right_3": [
        [ T,   T,   T,   T,  "dark","ear","dark", T  ],
        [ T,  "dark","dark","dark","fur","fur","fur","dark"],
        [ T,  "dark","fur","fur","eye","pupil","fur","dark"],
        ["dark","belly","fur","fur","eye","eye","nose","dark"],
        [ T,  "dark","belly","belly","belly","belly","dark", T  ],
        [ T,   T,   T,  "paw","paw", T,   T,   T  ],
    ],
    "walking_left_3": [
        [ T,  "dark","ear","dark", T,   T,   T,   T  ],
        ["dark","fur","fur","fur","dark","dark","dark", T  ],
        ["dark","fur","pupil","eye","fur","fur","dark", T  ],
        ["dark","nose","eye","eye","fur","fur","belly","dark"],
        [ T,  "dark","belly","belly","belly","belly","dark", T  ],
        [ T,   T,   T,  "paw","paw", T,   T,   T  ],
    ],
    # --- Frame 2 variants (animation alternates) ---
    # Walking: ear bounce (flattens into head) + paws together
    "walking_right_2": [
        [ T,   T,   T,   T,  "dark", T,  "dark", T  ],
        [ T,  "dark","dark","dark","fur","ear","fur","dark"],
        [ T,  "dark","fur","fur","eye","pupil","fur","dark"],
        ["dark","belly","fur","fur","eye","eye","nose","dark"],
        [ T,  "dark","belly","belly","belly","belly","dark", T  ],
        [ T,   T,  "paw", T,   T,  "paw", T,   T  ],
    ],
    "walking_left_2": [
        [ T,  "dark", T,  "dark", T,   T,   T,   T  ],
        ["dark","fur","ear","fur","dark","dark","dark", T  ],
        ["dark","fur","pupil","eye","fur","fur","dark", T  ],
        ["dark","nose","eye","eye","fur","fur","belly","dark"],
        [ T,  "dark","belly","belly","belly","belly","dark", T  ],
        [ T,   T,  "paw", T,   T,  "paw", T,   T  ],
    ],
    # Sleeping: body + underside expand outward (breathing)
    "sleeping_right_2": [
        [ T,   T,   T,   T,  "dark","ear","dark", T  ],
        [ T,  "dark","dark","dark","fur","fur","fur","dark"],
        [ T,  "dark","fur","fur","dark","dark","fur","dark"],
        ["dark","belly","belly","fur","fur","fur","belly","dark"],
        ["dark","belly","belly","belly","belly","belly","belly","dark"],
        [ T,   T,  "paw", T,   T,  "paw", T,   T  ],
    ],
    "sleeping_left_2": [
        [ T,  "dark","ear","dark", T,   T,   T,   T  ],
        ["dark","fur","fur","fur","dark","dark","dark", T  ],
        ["dark","fur","dark","dark","fur","fur","dark", T  ],
        ["dark","belly","fur","fur","fur","belly","belly","dark"],
        ["dark","belly","belly","belly","belly","belly","belly","dark"],
        [ T,   T,  "paw", T,   T,  "paw", T,   T  ],
    ],
}

# --- Far-zoom adult sprites (7w x 6h pixels -> 7x3 half-block chars) ---

PIG_PIXELS_FAR_ADULT = {
    "idle_right": [
        [ T,   T,  "dark","dark","dark","ear","dark"],
        [ T,  "dark","fur", "fur", "fur","fur","dark"],
        ["dark","fur", "fur", "fur","eye","pupil","dark"],
        ["dark","fur", "fur", "fur", "fur","nose","dark"],
        [ T,  "dark","belly","belly","belly","dark", T  ],
        [ T,   T,  "paw", T,  "paw", T,   T  ],
    ],
    "idle_left": [
        ["dark","ear","dark","dark","dark", T,   T  ],
        ["dark","fur", "fur", "fur","fur","dark", T  ],
        ["dark","pupil","eye","fur", "fur", "fur","dark"],
        ["dark","nose","fur", "fur", "fur", "fur","dark"],
        [ T,  "dark","belly","belly","belly","dark", T  ],
        [ T,   T,  "paw", T,  "paw", T,   T  ],
    ],
    # Walking frame 2: body bobs down (top row empty, paws tucked)
    "walking_right_2": [
        [ T,   T,   T,   T,   T,   T,   T  ],
        [ T,   T,  "dark","dark","dark","ear","dark"],
        [ T,  "dark","fur", "fur","eye","pupil","dark"],
        ["dark","fur", "fur", "fur", "fur","nose","dark"],
        [ T,  "dark","fur", "belly","belly","dark", T  ],
        [ T,  "dark","belly","belly","belly","dark", T  ],
    ],
    "walking_left_2": [
        [ T,   T,   T,   T,   T,   T,   T  ],
        ["dark","ear","dark","dark","dark", T,   T  ],
        ["dark","pupil","eye","fur", "fur","dark", T  ],
        ["dark","nose","fur", "fur", "fur", "fur","dark"],
        [ T,  "dark","belly","belly","fur","dark", T  ],
        [ T,  "dark","belly","belly","belly","dark", T  ],
    ],
    # Walking frame 3: body centred, paws closer together
    "walking_right_3": [
        [ T,   T,  "dark","dark","dark","ear","dark"],
        [ T,  "dark","fur", "fur", "fur","fur","dark"],
        ["dark","fur", "fur", "fur","eye","pupil","dark"],
        ["dark","fur", "fur", "fur", "fur","nose","dark"],
        [ T,  "dark","belly","belly","belly","dark", T  ],
        [ T,   T,   T,  "paw","paw", T,   T  ],
    ],
    "walking_left_3": [
        ["dark","ear","dark","dark","dark", T,   T  ],
        ["dark","fur", "fur", "fur","fur","dark", T  ],
        ["dark","pupil","eye","fur", "fur", "fur","dark"],
        ["dark","nose","fur", "fur", "fur", "fur","dark"],
        [ T,  "dark","belly","belly","belly","dark", T  ],
        [ T,   T,  "paw","paw", T,   T,   T  ],
    ],
    # Sleeping frame 2: belly widens (breathing)
    "sleeping_right_2": [
        [ T,   T,  "dark","dark","dark","ear","dark"],
        [ T,  "dark","fur", "fur", "fur","fur","dark"],
        ["dark","fur", "fur", "fur","dark","dark","dark"],
        ["dark","fur", "fur", "fur", "fur","fur","dark"],
        ["dark","belly","belly","belly","belly","belly","dark"],
        [ T,   T,  "paw", T,  "paw", T,   T  ],
    ],
    "sleeping_left_2": [
        ["dark","ear","dark","dark","dark", T,   T  ],
        ["dark","fur", "fur", "fur","fur","dark", T  ],
        ["dark","dark","dark","fur", "fur", "fur","dark"],
        ["dark","fur", "fur", "fur", "fur", "fur","dark"],
        ["dark","belly","belly","belly","belly","belly","dark"],
        [ T,   T,  "paw", T,  "paw", T,   T  ],
    ],
}

# --- Far-zoom baby sprites (5w x 4h pixels -> 5x2 half-block chars) ---

PIG_PIXELS_FAR_BABY = {
    "idle_right": [
        [ T,  "dark","dark","ear","dark"],
        ["dark","fur","eye","pupil","dark"],
        ["dark","fur", "fur","nose","dark"],
        [ T,  "dark","belly","dark", T  ],
    ],
    "idle_left": [
        ["dark","ear","dark","dark", T  ],
        ["dark","pupil","eye","fur","dark"],
        ["dark","nose","fur", "fur","dark"],
        [ T,  "dark","belly","dark", T  ],
    ],
    # Walking frame 2: body bobs down
    "walking_right_2": [
        [ T,   T,   T,   T,   T  ],
        [ T,  "dark","dark","ear","dark"],
        ["dark","fur","eye","pupil","dark"],
        ["dark","fur", "fur","nose","dark"],
    ],
    "walking_left_2": [
        [ T,   T,   T,   T,   T  ],
        ["dark","ear","dark","dark", T  ],
        ["dark","pupil","eye","fur","dark"],
        ["dark","nose","fur", "fur","dark"],
    ],
    # Walking frame 3: body centred, paws closer together
    "walking_right_3": [
        [ T,  "dark","dark","ear","dark"],
        ["dark","fur","eye","pupil","dark"],
        ["dark","fur", "fur","nose","dark"],
        [ T,   T,  "paw","paw", T  ],
    ],
    "walking_left_3": [
        ["dark","ear","dark","dark", T  ],
        ["dark","pupil","eye","fur","dark"],
        ["dark","nose","fur", "fur","dark"],
        [ T,  "paw","paw", T,   T  ],
    ],
}

# fmt: on
