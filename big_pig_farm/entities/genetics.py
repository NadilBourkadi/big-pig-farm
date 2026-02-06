"""Genetic system for guinea pigs - alleles, inheritance, and phenotype calculation."""

from enum import Enum
from typing import Self
import random

from pydantic import BaseModel


class Allele(str, Enum):
    """Genetic alleles for guinea pig traits."""
    # Extension locus (E) - controls black/color vs red/golden
    E = "E"   # Black/color (dominant)
    e = "e"   # Red/golden (recessive)

    # Brown locus (B) - modifies black to brown
    B = "B"   # Black (dominant)
    b = "b"   # Brown/chocolate (recessive)

    # Spotting locus (S) - controls white pattern
    S = "S"   # Solid color (dominant)
    s = "s"   # White spotting (recessive)

    # Color intensity locus (C)
    C = "C"     # Full color (dominant)
    ch = "ch"   # Chinchilla/diluted (recessive)

    # Roan locus (R)
    R = "R"   # Roan (dominant, lethal when homozygous)
    r = "r"   # Normal (recessive)


class BaseColor(str, Enum):
    """Base coat colors derived from E and B loci."""
    BLACK = "black"
    CHOCOLATE = "chocolate"
    GOLDEN = "golden"
    LIGHT_GOLDEN = "light_golden"


class Pattern(str, Enum):
    """Coat patterns derived from S locus."""
    SOLID = "solid"
    DUTCH = "dutch"  # Partial white spotting
    DALMATIAN = "dalmatian"  # Heavy white spotting


class ColorIntensity(str, Enum):
    """Color intensity from C locus."""
    FULL = "full"
    CHINCHILLA = "chinchilla"  # Diluted
    HIMALAYAN = "himalayan"  # Points only


class RoanType(str, Enum):
    """Roan pattern from R locus."""
    NONE = "none"
    ROAN = "roan"  # White hairs mixed in


class Rarity(str, Enum):
    """Rarity tier for guinea pig colors."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    VERY_RARE = "very_rare"
    LEGENDARY = "legendary"


class Genotype(BaseModel):
    """Complete genotype of a guinea pig."""
    # Each locus has two alleles (one from each parent)
    e_locus: tuple[str, str]  # Extension: (E/e, E/e)
    b_locus: tuple[str, str]  # Brown: (B/b, B/b)
    s_locus: tuple[str, str]  # Spotting: (S/s, S/s)
    c_locus: tuple[str, str]  # Color intensity: (C/ch, C/ch)
    r_locus: tuple[str, str]  # Roan: (R/r, R/r)

    @classmethod
    def random(cls) -> Self:
        """Generate a random common genotype."""
        return cls(
            e_locus=random.choice([("E", "E"), ("E", "e"), ("e", "e")]),
            b_locus=random.choice([("B", "B"), ("B", "b"), ("b", "b")]),
            s_locus=("S", "S"),  # Start with solid colors
            c_locus=("C", "C"),  # Full color
            r_locus=("r", "r"),  # No roan
        )

    @classmethod
    def random_common(cls) -> Self:
        """Generate a guaranteed common genotype."""
        return cls(
            e_locus=random.choice([("E", "E"), ("E", "e")]),
            b_locus=random.choice([("B", "B"), ("B", "b")]),
            s_locus=("S", "S"),
            c_locus=("C", "C"),
            r_locus=("r", "r"),
        )

    def has_dominant(self, locus: tuple[str, str], dominant: str) -> bool:
        """Check if a locus has at least one dominant allele."""
        return dominant in locus

    def is_homozygous_recessive(self, locus: tuple[str, str], recessive: str) -> bool:
        """Check if a locus is homozygous recessive."""
        return locus[0] == recessive and locus[1] == recessive

    def is_homozygous_dominant(self, locus: tuple[str, str], dominant: str) -> bool:
        """Check if a locus is homozygous dominant."""
        return locus[0] == dominant and locus[1] == dominant


class Phenotype(BaseModel):
    """Observable traits derived from genotype."""
    base_color: BaseColor
    pattern: Pattern
    intensity: ColorIntensity
    roan: RoanType
    rarity: Rarity

    @property
    def display_name(self) -> str:
        """Human-readable description of the phenotype."""
        parts = []

        if self.roan == RoanType.ROAN:
            parts.append("Roan")

        if self.intensity == ColorIntensity.CHINCHILLA:
            parts.append("Chinchilla")
        elif self.intensity == ColorIntensity.HIMALAYAN:
            parts.append("Himalayan")

        if self.pattern == Pattern.DUTCH:
            parts.append("Dutch")
        elif self.pattern == Pattern.DALMATIAN:
            parts.append("Dalmatian")

        # Base color
        color_names = {
            BaseColor.BLACK: "Black",
            BaseColor.CHOCOLATE: "Chocolate",
            BaseColor.GOLDEN: "Golden",
            BaseColor.LIGHT_GOLDEN: "Cream",
        }
        parts.append(color_names[self.base_color])

        return " ".join(parts)

    @property
    def ascii_color(self) -> str:
        """Rich color code for terminal display."""
        color_map = {
            BaseColor.BLACK: "grey23",
            BaseColor.CHOCOLATE: "orange4",
            BaseColor.GOLDEN: "gold1",
            BaseColor.LIGHT_GOLDEN: "wheat1",
        }
        return color_map.get(self.base_color, "white")


def calculate_phenotype(genotype: Genotype) -> Phenotype:
    """Calculate the observable phenotype from a genotype."""
    # Base color from E and B loci
    has_E = genotype.has_dominant(genotype.e_locus, "E")
    has_B = genotype.has_dominant(genotype.b_locus, "B")

    if has_E and has_B:
        base_color = BaseColor.BLACK
    elif has_E and not has_B:
        base_color = BaseColor.CHOCOLATE
    elif not has_E and has_B:
        base_color = BaseColor.GOLDEN
    else:
        base_color = BaseColor.LIGHT_GOLDEN

    # Pattern from S locus
    if genotype.is_homozygous_dominant(genotype.s_locus, "S"):
        pattern = Pattern.SOLID
    elif genotype.is_homozygous_recessive(genotype.s_locus, "s"):
        pattern = Pattern.DALMATIAN
    else:
        pattern = Pattern.DUTCH

    # Intensity from C locus
    if genotype.has_dominant(genotype.c_locus, "C"):
        intensity = ColorIntensity.FULL
    elif genotype.is_homozygous_recessive(genotype.c_locus, "ch"):
        intensity = ColorIntensity.HIMALAYAN
    else:
        intensity = ColorIntensity.CHINCHILLA

    # Roan from R locus
    if genotype.has_dominant(genotype.r_locus, "R"):
        roan = RoanType.ROAN
    else:
        roan = RoanType.NONE

    # Calculate rarity
    rarity = calculate_rarity(base_color, pattern, intensity, roan)

    return Phenotype(
        base_color=base_color,
        pattern=pattern,
        intensity=intensity,
        roan=roan,
        rarity=rarity,
    )


def calculate_rarity(
    base_color: BaseColor,
    pattern: Pattern,
    intensity: ColorIntensity,
    roan: RoanType,
) -> Rarity:
    """Calculate the rarity tier based on traits."""
    rare_count = 0

    # Pattern rarity
    if pattern == Pattern.DALMATIAN:
        rare_count += 2
    elif pattern == Pattern.DUTCH:
        rare_count += 1

    # Intensity rarity
    if intensity == ColorIntensity.HIMALAYAN:
        rare_count += 3
    elif intensity == ColorIntensity.CHINCHILLA:
        rare_count += 2

    # Roan is rare
    if roan == RoanType.ROAN:
        rare_count += 2

    # Chocolate and golden are slightly less common
    if base_color in (BaseColor.CHOCOLATE, BaseColor.LIGHT_GOLDEN):
        rare_count += 1

    # Determine tier
    if rare_count >= 6:
        return Rarity.LEGENDARY
    elif rare_count >= 4:
        return Rarity.VERY_RARE
    elif rare_count >= 2:
        return Rarity.RARE
    elif rare_count >= 1:
        return Rarity.UNCOMMON
    return Rarity.COMMON


def inherit_allele(parent1_locus: tuple[str, str], parent2_locus: tuple[str, str]) -> tuple[str, str]:
    """Inherit one allele from each parent for a locus."""
    allele1 = random.choice(parent1_locus)
    allele2 = random.choice(parent2_locus)
    return (allele1, allele2)


def breed(parent1: Genotype, parent2: Genotype) -> Genotype:
    """Create offspring genotype from two parents."""
    # Check for lethal roan combination
    child_r = inherit_allele(parent1.r_locus, parent2.r_locus)
    if child_r[0] == "R" and child_r[1] == "R":
        # Lethal - re-roll (in real genetics this would be stillborn)
        # We handle gracefully by re-rolling
        while child_r[0] == "R" and child_r[1] == "R":
            child_r = inherit_allele(parent1.r_locus, parent2.r_locus)

    return Genotype(
        e_locus=inherit_allele(parent1.e_locus, parent2.e_locus),
        b_locus=inherit_allele(parent1.b_locus, parent2.b_locus),
        s_locus=inherit_allele(parent1.s_locus, parent2.s_locus),
        c_locus=inherit_allele(parent1.c_locus, parent2.c_locus),
        r_locus=child_r,
    )


def predict_offspring_probabilities(
    parent1: Genotype, parent2: Genotype
) -> dict[str, float]:
    """Predict probability of offspring phenotypes using Punnett squares."""
    # This is a simplified calculation - for full accuracy we'd enumerate all combinations
    phenotype_counts: dict[str, int] = {}
    total = 1000  # Sample size for probability estimation

    for _ in range(total):
        child = breed(parent1, parent2)
        phenotype = calculate_phenotype(child)
        name = phenotype.display_name
        phenotype_counts[name] = phenotype_counts.get(name, 0) + 1

    return {name: count / total for name, count in phenotype_counts.items()}
