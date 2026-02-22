"""Genetic system for guinea pigs - alleles, inheritance, and phenotype calculation."""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Self

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

    # Dilution locus (D)
    D = "D"   # Full color (dominant)
    d = "d"   # Diluted (recessive)


class BaseColor(str, Enum):
    """Base coat colors derived from E, B, and D loci."""
    BLACK = "black"
    CHOCOLATE = "chocolate"
    GOLDEN = "golden"
    CREAM = "cream"
    BLUE = "blue"         # Diluted black (dd)
    LILAC = "lilac"       # Diluted chocolate (bb + dd)
    SAFFRON = "saffron"   # Diluted golden (ee + dd)
    SMOKE = "smoke"       # Diluted cream (ee + bb + dd)


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
    d_locus: tuple[str, str] = ("D", "D")  # Dilution: (D/d, D/d)

    @classmethod
    def random(cls) -> Self:
        """Generate a random common genotype."""
        return cls(
            e_locus=random.choice([("E", "E"), ("E", "e"), ("e", "e")]),
            b_locus=random.choice([("B", "B"), ("B", "b"), ("b", "b")]),
            s_locus=("S", "S"),  # Start with solid colors
            c_locus=("C", "C"),  # Full color
            r_locus=("r", "r"),  # No roan
            d_locus=("D", "D"),  # Full color (not diluted)
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
            d_locus=("D", "D"),
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
            BaseColor.CREAM: "Cream",
            BaseColor.BLUE: "Blue",
            BaseColor.LILAC: "Lilac",
            BaseColor.SAFFRON: "Saffron",
            BaseColor.SMOKE: "Smoke",
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
            BaseColor.CREAM: "wheat1",
            BaseColor.BLUE: "steel_blue1",
            BaseColor.LILAC: "plum1",
            BaseColor.SAFFRON: "dark_orange",
            BaseColor.SMOKE: "grey62",
        }
        return color_map.get(self.base_color, "white")


def _determine_base_color(has_E: bool, has_B: bool, has_D: bool = True) -> BaseColor:
    """Determine base coat color from E, B, and D locus dominance."""
    if has_E and has_B:
        return BaseColor.BLACK if has_D else BaseColor.BLUE
    elif has_E and not has_B:
        return BaseColor.CHOCOLATE if has_D else BaseColor.LILAC
    elif not has_E and has_B:
        return BaseColor.GOLDEN if has_D else BaseColor.SAFFRON
    else:
        return BaseColor.CREAM if has_D else BaseColor.SMOKE


def calculate_phenotype(genotype: Genotype) -> Phenotype:
    """Calculate the observable phenotype from a genotype."""
    # Base color from E, B, and D loci
    has_E = genotype.has_dominant(genotype.e_locus, "E")
    has_B = genotype.has_dominant(genotype.b_locus, "B")
    has_D = genotype.has_dominant(genotype.d_locus, "D")
    base_color = _determine_base_color(has_E, has_B, has_D)

    # Pattern from S locus
    if genotype.is_homozygous_dominant(genotype.s_locus, "S"):
        pattern = Pattern.SOLID
    elif genotype.is_homozygous_recessive(genotype.s_locus, "s"):
        pattern = Pattern.DALMATIAN
    else:
        pattern = Pattern.DUTCH

    # Intensity from C locus
    if genotype.is_homozygous_recessive(genotype.c_locus, "ch"):
        intensity = ColorIntensity.HIMALAYAN
    elif "ch" in genotype.c_locus:
        intensity = ColorIntensity.CHINCHILLA
    else:
        intensity = ColorIntensity.FULL

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
    if base_color in (BaseColor.CHOCOLATE, BaseColor.CREAM):
        rare_count += 1

    # Diluted colors require dd (homozygous recessive)
    if base_color == BaseColor.BLUE:
        rare_count += 2
    elif base_color == BaseColor.LILAC:
        rare_count += 3  # bb + dd
    elif base_color == BaseColor.SAFFRON:
        rare_count += 3  # ee + dd
    elif base_color == BaseColor.SMOKE:
        rare_count += 4  # ee + bb + dd

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


@dataclass
class BreedResult:
    """Result of breeding two guinea pigs."""
    genotype: Genotype
    mutations: list[str] = field(default_factory=list)


# Locus definitions for mutation system: (locus_name, dominant, recessive)
LOCUS_DEFINITIONS: list[tuple[str, str, str]] = [
    ("e_locus", "E", "e"),
    ("b_locus", "B", "b"),
    ("s_locus", "S", "s"),
    ("c_locus", "C", "ch"),
    ("r_locus", "R", "r"),
    ("d_locus", "D", "d"),
]

# Human-readable names for mutation logging
LOCUS_DISPLAY_NAMES: dict[str, str] = {
    "e_locus": "Extension",
    "b_locus": "Brown",
    "s_locus": "Spotted",
    "c_locus": "Intensity",
    "r_locus": "Roan",
    "d_locus": "Dilution",
}


def inherit_allele(parent1_locus: tuple[str, str], parent2_locus: tuple[str, str]) -> tuple[str, str]:
    """Inherit one allele from each parent for a locus."""
    allele1 = random.choice(parent1_locus)
    allele2 = random.choice(parent2_locus)
    return (allele1, allele2)


def mutate_locus(
    locus: tuple[str, str],
    dominant: str,
    recessive: str,
    rate: float,
) -> tuple[tuple[str, str], bool]:
    """Attempt to mutate one allele in a locus.

    Returns (new_locus, did_mutate). Flips one random allele:
    dominant -> recessive or recessive -> dominant.
    """
    if random.random() >= rate:
        return locus, False

    # Pick a random allele position to mutate
    idx = random.randint(0, 1)
    allele = locus[idx]

    if allele == dominant:
        new_allele = recessive
    else:
        new_allele = dominant

    new_locus = list(locus)
    new_locus[idx] = new_allele
    return tuple(new_locus), True


def mutate_locus_directional(
    locus: tuple[str, str],
    target_allele: str,
    rate: float,
) -> tuple[tuple[str, str], bool]:
    """Attempt a directional mutation — push one allele toward the target.

    Picks a random allele position (0 or 1). If that allele is NOT the
    target, replace it with the target (mutation occurs). If already the
    target, the roll is wasted (no mutation).
    """
    if random.random() >= rate:
        return locus, False

    idx = random.randint(0, 1)
    if locus[idx] == target_allele:
        return locus, False  # Already matches — wasted roll

    new_locus = list(locus)
    new_locus[idx] = target_allele
    return tuple(new_locus), True


def breed(
    parent1: Genotype,
    parent2: Genotype,
    mutation_rate: float = 0.0,
    locus_rates: dict[str, float] | None = None,
    directional_targets: dict[str, str] | None = None,
    directional_rate: float = 0.0,
) -> BreedResult:
    """Create offspring genotype from two parents with optional mutations.

    Args:
        parent1: First parent genotype
        parent2: Second parent genotype
        mutation_rate: Per-locus mutation rate (0.0 = no mutations, 0.02 = 2%)
        locus_rates: Optional per-locus overrides (e.g. from biome boosts).
            Keys are locus names like "e_locus", "b_locus", etc.
        directional_targets: Optional per-locus target alleles for directional
            mutations (e.g. {"e_locus": "e", "b_locus": "b"}).
        directional_rate: Rate for directional mutations at targeted loci.

    Returns:
        BreedResult with genotype and list of mutation descriptions
    """
    # Normal Mendelian inheritance
    child_e = inherit_allele(parent1.e_locus, parent2.e_locus)
    child_b = inherit_allele(parent1.b_locus, parent2.b_locus)
    child_s = inherit_allele(parent1.s_locus, parent2.s_locus)
    child_c = inherit_allele(parent1.c_locus, parent2.c_locus)
    child_r = inherit_allele(parent1.r_locus, parent2.r_locus)
    child_d = inherit_allele(parent1.d_locus, parent2.d_locus)

    # Check for lethal roan combination
    if child_r[0] == "R" and child_r[1] == "R":
        while child_r[0] == "R" and child_r[1] == "R":
            child_r = inherit_allele(parent1.r_locus, parent2.r_locus)

    # Apply mutations
    mutations = []
    loci = {
        "e_locus": (child_e, "E", "e"),
        "b_locus": (child_b, "B", "b"),
        "s_locus": (child_s, "S", "s"),
        "c_locus": (child_c, "C", "ch"),
        "r_locus": (child_r, "R", "r"),
        "d_locus": (child_d, "D", "d"),
    }

    has_mutations = mutation_rate > 0 or locus_rates or directional_targets
    if has_mutations:
        for locus_name, (locus_val, dom, rec) in loci.items():
            # Directional mutation for targeted loci
            if directional_targets and locus_name in directional_targets and directional_rate > 0:
                target_allele = directional_targets[locus_name]
                new_val, did_mutate = mutate_locus_directional(locus_val, target_allele, directional_rate)
            else:
                # Random mutation at per-locus or base rate
                rate = locus_rates.get(locus_name, mutation_rate) if locus_rates else mutation_rate
                if rate <= 0:
                    continue
                new_val, did_mutate = mutate_locus(locus_val, dom, rec, rate)
            if did_mutate:
                # If mutation creates RR (lethal), suppress it entirely
                if locus_name == "r_locus" and new_val[0] == "R" and new_val[1] == "R":
                    continue
                loci[locus_name] = (new_val, dom, rec)
                display = LOCUS_DISPLAY_NAMES[locus_name]
                mutations.append(f"{display} ({locus_val[0]}/{locus_val[1]} -> {new_val[0]}/{new_val[1]})")

    genotype = Genotype(
        e_locus=loci["e_locus"][0],
        b_locus=loci["b_locus"][0],
        s_locus=loci["s_locus"][0],
        c_locus=loci["c_locus"][0],
        r_locus=loci["r_locus"][0],
        d_locus=loci["d_locus"][0],
    )

    return BreedResult(genotype=genotype, mutations=mutations)


def carrier_summary(genotype: Genotype) -> str:
    """Get a short summary of hidden carrier alleles in a genotype."""
    carriers = []
    g = genotype
    if g.e_locus[0] != g.e_locus[1] and "e" in g.e_locus:
        carriers.append("E/e")
    if g.b_locus[0] != g.b_locus[1] and "b" in g.b_locus:
        carriers.append("B/b")
    if g.s_locus[0] != g.s_locus[1] and "s" in g.s_locus:
        carriers.append("S/s")
    if g.c_locus[0] != g.c_locus[1] and "ch" in g.c_locus:
        carriers.append("C/ch")
    if "R" in g.r_locus and "r" in g.r_locus:
        carriers.append("R/r")
    if g.d_locus[0] != g.d_locus[1] and "d" in g.d_locus:
        carriers.append("D/d")
    return ", ".join(carriers) if carriers else "None"


def predict_offspring_phenotypes(
    parent1: Genotype, parent2: Genotype
) -> list[tuple[Phenotype, float]]:
    """Predict offspring phenotype probabilities, returning Phenotype objects.

    Returns a list of (Phenotype, probability) tuples sorted by probability descending.
    Uses the same Monte Carlo sampling as predict_offspring_probabilities.
    """
    phenotype_counts: dict[str, tuple[Phenotype, int]] = {}
    total = 1000

    for _ in range(total):
        result = breed(parent1, parent2)
        phenotype = calculate_phenotype(result.genotype)
        name = phenotype.display_name
        if name in phenotype_counts:
            phenotype_counts[name] = (phenotype_counts[name][0], phenotype_counts[name][1] + 1)
        else:
            phenotype_counts[name] = (phenotype, 1)

    results = [(pheno, count / total) for pheno, count in phenotype_counts.values()]
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def calculate_target_probability(
    parent1: Genotype,
    parent2: Genotype,
    target_colors: set[BaseColor],
    target_patterns: set[Pattern],
    target_intensities: set[ColorIntensity],
    target_roan: set[RoanType],
) -> float:
    """Compute exact P(offspring matches target) via analytical Punnett squares.

    Per-locus probabilities are multiplied across independent loci.
    Empty target set on any axis means probability 1.0 (any value OK).
    """
    p_color = _color_probability(parent1, parent2, target_colors) if target_colors else 1.0
    p_pattern = _pattern_probability(parent1, parent2, target_patterns) if target_patterns else 1.0
    p_intensity = _intensity_probability(parent1, parent2, target_intensities) if target_intensities else 1.0
    p_roan = _roan_probability(parent1, parent2, target_roan) if target_roan else 1.0

    return p_color * p_pattern * p_intensity * p_roan


def _locus_outcome_probs(
    p1_locus: tuple[str, str],
    p2_locus: tuple[str, str],
) -> dict[tuple[str, str], float]:
    """Compute all possible offspring genotype combinations for a single locus.

    Returns dict mapping (allele1, allele2) -> probability.
    Each parent passes one allele with 50% chance, giving 4 equally likely combos.
    """
    outcomes: dict[tuple[str, str], float] = {}
    for a1 in p1_locus:
        for a2 in p2_locus:
            key = (a1, a2)
            outcomes[key] = outcomes.get(key, 0.0) + 0.25
    return outcomes


def _has_dominant_allele(locus: tuple[str, str], dominant: str) -> bool:
    """Check if a locus pair contains at least one dominant allele."""
    return dominant in locus


def _is_homozygous(locus: tuple[str, str], allele: str) -> bool:
    """Check if a locus pair is homozygous for a given allele."""
    return locus[0] == allele and locus[1] == allele


def _color_probability(
    p1: Genotype,
    p2: Genotype,
    targets: set[BaseColor],
) -> float:
    """P(offspring color in targets). Color depends on E+B+D loci jointly."""
    e_outcomes = _locus_outcome_probs(p1.e_locus, p2.e_locus)
    b_outcomes = _locus_outcome_probs(p1.b_locus, p2.b_locus)
    d_outcomes = _locus_outcome_probs(p1.d_locus, p2.d_locus)

    prob = 0.0
    for e_alleles, e_prob in e_outcomes.items():
        has_E = _has_dominant_allele(e_alleles, "E")
        for b_alleles, b_prob in b_outcomes.items():
            has_B = _has_dominant_allele(b_alleles, "B")
            for d_alleles, d_prob in d_outcomes.items():
                has_D = _has_dominant_allele(d_alleles, "D")

                color = _determine_base_color(has_E, has_B, has_D)

                if color in targets:
                    prob += e_prob * b_prob * d_prob

    return prob


def _pattern_probability(
    p1: Genotype,
    p2: Genotype,
    targets: set[Pattern],
) -> float:
    """P(offspring pattern in targets). Pattern depends on S locus."""
    outcomes = _locus_outcome_probs(p1.s_locus, p2.s_locus)

    prob = 0.0
    for alleles, p in outcomes.items():
        if _is_homozygous(alleles, "S"):
            pattern = Pattern.SOLID
        elif _is_homozygous(alleles, "s"):
            pattern = Pattern.DALMATIAN
        else:
            pattern = Pattern.DUTCH

        if pattern in targets:
            prob += p

    return prob


def _intensity_probability(
    p1: Genotype,
    p2: Genotype,
    targets: set[ColorIntensity],
) -> float:
    """P(offspring intensity in targets). Intensity depends on C locus."""
    outcomes = _locus_outcome_probs(p1.c_locus, p2.c_locus)

    prob = 0.0
    for alleles, p in outcomes.items():
        if _has_dominant_allele(alleles, "C"):
            intensity = ColorIntensity.FULL
        elif _is_homozygous(alleles, "ch"):
            intensity = ColorIntensity.HIMALAYAN
        else:
            intensity = ColorIntensity.CHINCHILLA

        if intensity in targets:
            prob += p

    return prob


def _roan_probability(
    p1: Genotype,
    p2: Genotype,
    targets: set[RoanType],
) -> float:
    """P(offspring roan in targets). Roan depends on R locus.

    RR is lethal and gets rerolled, so the game re-inherits until non-RR.
    This effectively redistributes RR probability proportionally across
    surviving outcomes: each non-RR outcome gets p / (1 - p_RR).
    """
    outcomes = _locus_outcome_probs(p1.r_locus, p2.r_locus)

    # Find probability of lethal RR
    rr_lethal_prob = sum(
        p for alleles, p in outcomes.items()
        if alleles[0] == "R" and alleles[1] == "R"
    )

    if rr_lethal_prob >= 1.0:
        # Both parents RR — impossible in practice (lethal), but handle gracefully
        # Reroll always produces Rr per game code
        return 1.0 if RoanType.ROAN in targets else 0.0

    prob = 0.0
    for alleles, p in outcomes.items():
        if alleles[0] == "R" and alleles[1] == "R":
            continue

        # Rescale probability to account for RR elimination
        adjusted_p = p / (1.0 - rr_lethal_prob)
        roan = RoanType.ROAN if _has_dominant_allele(alleles, "R") else RoanType.NONE

        if roan in targets:
            prob += adjusted_p

    return prob
