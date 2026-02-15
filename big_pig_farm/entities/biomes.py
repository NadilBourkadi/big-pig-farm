"""Biome definitions for farm areas."""

from dataclasses import dataclass, field
from enum import Enum


class BiomeType(str, Enum):
    """Types of biomes for farm areas."""
    MEADOW = "meadow"
    BURROW = "burrow"
    GARDEN = "garden"
    TROPICAL = "tropical"
    ALPINE = "alpine"
    CRYSTAL = "crystal"
    WILDFLOWER = "wildflower"
    SANCTUARY = "sanctuary"


@dataclass(frozen=True)
class BiomeInfo:
    """Metadata for a biome type."""
    display_name: str
    description: str
    required_tier: int
    cost: int

    # Floor rendering
    floor_chars: list[str]
    floor_colors: list[str]
    floor_bg: str

    # Wall tint (optional override for WALL_PLANK/WALL_GRAIN colors)
    wall_tint_plank: list[str] = field(default_factory=list)
    wall_tint_grain: list[str] = field(default_factory=list)

    # Mutation boost: locus_name -> extra per-locus rate
    mutation_boost_loci: dict[str, float] = field(default_factory=dict)

    # Happiness bonus per game hour when pig is in preferred biome
    happiness_bonus: float = 0.0


BIOMES: dict[BiomeType, BiomeInfo] = {
    BiomeType.MEADOW: BiomeInfo(
        display_name="Meadow",
        description="Lush green grass — a natural home for guinea pigs",
        required_tier=1,
        cost=0,
        floor_chars=["♣", "·", "'", ",", ".", '"', "`"],
        floor_colors=["#4a8a3a", "#3d7a30", "#55964a", "#3a7028", "#4d8e40", "#5a9a50"],
        floor_bg="#2d5a1e",
        happiness_bonus=0.5,
    ),
    BiomeType.BURROW: BiomeInfo(
        display_name="Burrow",
        description="Dark earthy tunnels — cozy and warm",
        required_tier=1,
        cost=300,
        floor_chars=["·", ".", "~", ":", "'", ","],
        floor_colors=["#6a5040", "#5e4535", "#7a6050", "#6e5545", "#584030", "#756555"],
        floor_bg="#3a2d1a",
        wall_tint_plank=["#7a5a30", "#8a6a40", "#6a4a20", "#8a6535", "#7a5525"],
        wall_tint_grain=["#4a3018", "#3c2510", "#5a4020"],
        mutation_boost_loci={"b_locus": 0.01},
        happiness_bonus=0.5,
    ),
    BiomeType.GARDEN: BiomeInfo(
        display_name="Garden",
        description="A lush vegetable garden with rich soil",
        required_tier=2,
        cost=600,
        floor_chars=["♣", ".", "·", "'", ",", "~"],
        floor_colors=["#3a8a3a", "#2d7a2d", "#48964a", "#358a35", "#40904a", "#509a45"],
        floor_bg="#1e4a1e",
        wall_tint_plank=["#6a8a40", "#7a9a50", "#5a7a30", "#6a8535", "#7a9045"],
        wall_tint_grain=["#3a5020", "#2c4018", "#4a6028"],
        mutation_boost_loci={"e_locus": 0.01},
        happiness_bonus=0.8,
    ),
    BiomeType.TROPICAL: BiomeInfo(
        display_name="Tropical",
        description="Warm and exotic — palm fronds and sandy floors",
        required_tier=2,
        cost=800,
        floor_chars=["~", "'", "·", ",", ".", '"'],
        floor_colors=["#8a7040", "#7a6535", "#9a8050", "#8a7545", "#7a6030", "#9a8a55"],
        floor_bg="#5a4020",
        wall_tint_plank=["#a08050", "#b09060", "#907040", "#a08555", "#b09565"],
        wall_tint_grain=["#6a5030", "#5c4020", "#7a6040"],
        mutation_boost_loci={"s_locus": 0.01},
        happiness_bonus=0.8,
    ),
    BiomeType.ALPINE: BiomeInfo(
        display_name="Alpine",
        description="Cool mountain rocks with grey-blue stone floors",
        required_tier=3,
        cost=1200,
        floor_chars=["·", "^", ".", ",", "'", "`"],
        floor_colors=["#708090", "#607080", "#809098", "#6a7a88", "#587080", "#8a9aa0"],
        floor_bg="#3a4a5a",
        wall_tint_plank=["#708090", "#809098", "#607080", "#6a7a88", "#7a8a98"],
        wall_tint_grain=["#405060", "#354550", "#506070"],
        mutation_boost_loci={"c_locus": 0.01},
        happiness_bonus=1.0,
    ),
    BiomeType.CRYSTAL: BiomeInfo(
        display_name="Crystal Cave",
        description="A mysterious cave with glowing purple crystals",
        required_tier=3,
        cost=1500,
        floor_chars=["·", ".", "*", ",", "'", "`"],
        floor_colors=["#8060a0", "#705090", "#9070b0", "#7a60a0", "#6a5090", "#9a80b0"],
        floor_bg="#2a2040",
        wall_tint_plank=["#6050a0", "#7060b0", "#504090", "#6555a5", "#7565b5"],
        wall_tint_grain=["#302850", "#252040", "#403860"],
        mutation_boost_loci={"r_locus": 0.01},
        happiness_bonus=1.0,
    ),
    BiomeType.WILDFLOWER: BiomeInfo(
        display_name="Wildflower",
        description="A colorful field bursting with wildflowers",
        required_tier=4,
        cost=2000,
        floor_chars=["♣", "·", ",", "'", ".", "~"],
        floor_colors=["#6a9a40", "#5a8a30", "#80aa50", "#509a40", "#70aa45", "#60a035"],
        floor_bg="#3a5a20",
        wall_tint_plank=["#8aaa50", "#9aba60", "#7a9a40", "#8aa555", "#9ab565"],
        wall_tint_grain=["#4a6028", "#3c5020", "#5a7030"],
        mutation_boost_loci={"s_locus": 0.005, "e_locus": 0.005},
        happiness_bonus=1.2,
    ),
    BiomeType.SANCTUARY: BiomeInfo(
        display_name="Sanctuary",
        description="A golden temple of tranquility — all mutations enhanced",
        required_tier=5,
        cost=3500,
        floor_chars=["·", ".", ",", "'", "`", "~"],
        floor_colors=["#b0a060", "#a09050", "#c0b070", "#aa9a60", "#9a8a50", "#c0b575"],
        floor_bg="#4a4030",
        wall_tint_plank=["#b0a060", "#c0b070", "#a09050", "#b0a565", "#c0b575"],
        wall_tint_grain=["#6a5830", "#5c4a28", "#7a6838"],
        mutation_boost_loci={
            "e_locus": 0.005,
            "b_locus": 0.005,
            "s_locus": 0.005,
            "c_locus": 0.005,
            "r_locus": 0.005,
        },
        happiness_bonus=1.5,
    ),
}
