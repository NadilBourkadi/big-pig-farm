#!/usr/bin/env python3
"""Preview tool for half-block pig sprites, portraits, and facility sprites.

Usage:
    poetry run python tools/preview_sprite.py [--sprites] [--portraits] [--facilities] [--all]

Renders pig sprites, portraits, and/or facility sprites to the terminal
so you can visually verify the half-block rendering pipeline.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console

from big_pig_farm.data.sprite_engine import (
    convert_pixels,
    render_to_rich_text,
    PALETTES,
)
from big_pig_farm.data.pig_portraits import generate_portrait
from big_pig_farm.data.pig_sprites import PIG_PIXELS_ADULT, PIG_PIXELS_BABY
from big_pig_farm.data.facility_pixels import (
    FACILITY_PALETTES,
    FACILITY_PIXELS,
    FACILITY_PIXELS_FAR,
)
from big_pig_farm.data.facility_pixels_close import FACILITY_PIXELS_CLOSE
from big_pig_farm.data.pig_sprites_close import PIG_PIXELS_CLOSE_ADULT, PIG_PIXELS_CLOSE_BABY

console = Console()


def preview_sprites() -> None:
    """Render all pig sprites at normal zoom for each color."""
    console.print("\n[bold underline]PIG SPRITES (Normal Zoom)[/]\n")

    colors = ["BLACK", "CHOCOLATE", "GOLDEN", "CREAM"]
    states = ["idle_right", "idle_left", "walking_right", "eating_right", "sleeping_right", "happy_right", "sad_right"]

    for color in colors:
        console.print(f"[bold]{color}[/]")
        palette = PALETTES[color]

        for state in states:
            if state not in PIG_PIXELS_ADULT:
                continue
            grid = PIG_PIXELS_ADULT[state]
            converted = convert_pixels(grid, palette)
            rich_text = render_to_rich_text(converted)

            label = state.replace("_", " ").title()
            console.print(f"  {label}:")
            # Indent each line
            for line in rich_text.split():
                console.print(f"    ", end="")
                console.print(line)
            console.print()

    # Baby sprites
    console.print("[bold]BABY SPRITES (Black)[/]")
    palette = PALETTES["BLACK"]
    for state in ["idle_right", "idle_left", "walking_right", "sleeping_right"]:
        if state not in PIG_PIXELS_BABY:
            continue
        grid = PIG_PIXELS_BABY[state]
        converted = convert_pixels(grid, palette)
        rich_text = render_to_rich_text(converted)
        label = state.replace("_", " ").title()
        console.print(f"  {label}:")
        for line_text in str(rich_text).split("\n"):
            console.print(f"    {line_text}")
        console.print()


def preview_sprites_close() -> None:
    """Render all pig sprites at close zoom for each color."""
    console.print("\n[bold underline]PIG SPRITES (Close Zoom)[/]\n")

    colors = ["BLACK", "CHOCOLATE", "GOLDEN", "CREAM"]
    states = [
        "idle_right", "walking_right", "walking_right_1",
        "eating_right", "eating_right_1",
        "sleeping_right", "sleeping_right_1",
        "happy_right", "sad_right",
    ]

    for color in colors:
        console.print(f"[bold]{color}[/]")
        palette = PALETTES[color]

        for state in states:
            if state not in PIG_PIXELS_CLOSE_ADULT:
                continue
            grid = PIG_PIXELS_CLOSE_ADULT[state]
            converted = convert_pixels(grid, palette)
            rich_text = render_to_rich_text(converted)
            label = state.replace("_", " ").title()
            console.print(f"  {label}:")
            for line in rich_text.split():
                console.print(f"    ", end="")
                console.print(line)
            console.print()

    # Baby close-zoom
    console.print("[bold]BABY SPRITES — Close Zoom (Black)[/]")
    palette = PALETTES["BLACK"]
    for state in ["idle_right", "walking_right", "walking_right_1", "sleeping_right", "sleeping_right_1"]:
        if state not in PIG_PIXELS_CLOSE_BABY:
            continue
        grid = PIG_PIXELS_CLOSE_BABY[state]
        converted = convert_pixels(grid, palette)
        rich_text = render_to_rich_text(converted)
        label = state.replace("_", " ").title()
        console.print(f"  {label}:")
        for line in rich_text.split():
            console.print(f"    ", end="")
            console.print(line)
        console.print()


def preview_portraits() -> None:
    """Render sample portraits for various phenotype combinations."""
    console.print("\n[bold underline]PIG PORTRAITS (32x24 -> 32x12 half-block)[/]\n")

    samples = [
        ("BLACK",     "solid",     "full",       "none",  "pig-001"),
        ("CHOCOLATE", "solid",     "full",       "none",  "pig-002"),
        ("GOLDEN",    "solid",     "full",       "none",  "pig-003"),
        ("CREAM",     "solid",     "full",       "none",  "pig-004"),
        ("BLACK",     "dutch",     "full",       "none",  "pig-005"),
        ("CHOCOLATE", "dalmatian", "full",       "none",  "pig-006"),
        ("GOLDEN",    "solid",     "himalayan",  "none",  "pig-007"),
        ("CREAM",     "solid",     "chinchilla", "none",  "pig-008"),
        ("BLACK",     "solid",     "full",       "roan",  "pig-009"),
        ("CHOCOLATE", "dutch",     "chinchilla", "roan",  "pig-010"),
        ("GOLDEN",    "dalmatian", "himalayan",  "roan",  "pig-011"),
        ("CREAM",     "dalmatian", "chinchilla", "none",  "pig-012"),
    ]

    for color, pattern, intensity, roan, pid in samples:
        label = f"{color} {pattern} {intensity}"
        if roan == "roan":
            label += " ROAN"

        console.print(f"[bold]{label}[/]  (id={pid})")
        grid = generate_portrait(color, pattern, intensity, roan, pid)
        palette = PALETTES[color]
        converted = convert_pixels(grid, palette)
        rich = render_to_rich_text(converted)
        console.print(rich)
        console.print()


def preview_determinism() -> None:
    """Verify that the same pig ID always produces the same portrait."""
    console.print("\n[bold underline]DETERMINISM CHECK[/]\n")

    pid = "test-uuid-deterministic"
    grid1 = generate_portrait("BLACK", "dalmatian", "full", "roan", pid)
    grid2 = generate_portrait("BLACK", "dalmatian", "full", "roan", pid)

    if grid1 == grid2:
        console.print("[green]PASS[/] — Same pig ID produces identical portrait")
    else:
        console.print("[red]FAIL[/] — Portraits differ for same pig ID!")

    grid3 = generate_portrait("BLACK", "dalmatian", "full", "roan", "different-pig")
    if grid1 != grid3:
        console.print("[green]PASS[/] — Different pig IDs produce different portraits")
    else:
        console.print("[yellow]WARN[/] — Different pig IDs produced same portrait (unlikely)")


def preview_facilities() -> None:
    """Render all facility sprites at all zoom levels."""
    # Facility types that have state variants (consumables)
    consumable_types = {"food_bowl", "water_bottle", "hay_rack"}

    # All facility types in order
    facility_types = [
        "food_bowl", "water_bottle", "hay_rack", "hideout",
        "exercise_wheel", "tunnel", "play_area", "breeding_den",
        "nursery", "veggie_garden", "grooming_station", "genetics_lab",
    ]

    # --- Normal zoom ---
    console.print("\n[bold underline]FACILITY SPRITES (Normal Zoom)[/]\n")
    for ftype in facility_types:
        palette = FACILITY_PALETTES.get(ftype)
        if palette is None:
            continue

        label = ftype.replace("_", " ").title()
        states = ["default"]
        if ftype in consumable_types:
            states = ["default", "empty", "full"]

        for state_name in states:
            key = ftype if state_name == "default" else f"{ftype}_{state_name}"
            grid = FACILITY_PIXELS.get(key)
            if grid is None:
                continue
            converted = convert_pixels(grid, palette)
            rich_text = render_to_rich_text(converted)
            console.print(f"  [bold]{label}[/] ({state_name}):")
            for line in rich_text.split():
                console.print(f"    ", end="")
                console.print(line)
            console.print()

    # --- Far zoom ---
    console.print("[bold underline]FACILITY SPRITES (Far Zoom)[/]\n")
    for ftype in facility_types:
        palette = FACILITY_PALETTES.get(ftype)
        if palette is None:
            continue

        grid = FACILITY_PIXELS_FAR.get(ftype)
        if grid is None:
            continue

        label = ftype.replace("_", " ").title()
        converted = convert_pixels(grid, palette)
        rich_text = render_to_rich_text(converted)
        console.print(f"  [bold]{label}[/]:")
        for line in rich_text.split():
            console.print(f"    ", end="")
            console.print(line)
        console.print()

    # --- Close zoom (hand-crafted) ---
    console.print("[bold underline]FACILITY SPRITES (Close Zoom)[/]\n")
    for ftype in facility_types:
        palette = FACILITY_PALETTES.get(ftype)
        if palette is None:
            continue

        label = ftype.replace("_", " ").title()
        states = ["default"]
        if ftype in consumable_types:
            states = ["default", "empty", "full"]

        for state_name in states:
            key = ftype if state_name == "default" else f"{ftype}_{state_name}"
            grid = FACILITY_PIXELS_CLOSE.get(key)
            if grid is None:
                continue
            converted = convert_pixels(grid, palette)
            rich_text = render_to_rich_text(converted)
            console.print(f"  [bold]{label}[/] ({state_name}):")
            for line in rich_text.split():
                console.print(f"    ", end="")
                console.print(line)
            console.print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview half-block pig sprites, portraits, and facilities")
    parser.add_argument("--sprites", action="store_true", help="Show pig sprites")
    parser.add_argument("--portraits", action="store_true", help="Show pig portraits")
    parser.add_argument("--facilities", action="store_true", help="Show facility sprites")
    parser.add_argument("--all", action="store_true", help="Show everything")
    args = parser.parse_args()

    if not (args.sprites or args.portraits or args.facilities or args.all):
        args.all = True

    if args.sprites or args.all:
        preview_sprites()
        preview_sprites_close()

    if args.portraits or args.all:
        preview_portraits()
        preview_determinism()

    if args.facilities or args.all:
        preview_facilities()


if __name__ == "__main__":
    main()
