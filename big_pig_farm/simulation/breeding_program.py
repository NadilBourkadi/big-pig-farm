"""Breeding program - goal-oriented autopilot for selective breeding."""

from enum import Enum

from pydantic import BaseModel, Field

from big_pig_farm.entities.genetics import (
    BaseColor,
    Pattern,
    ColorIntensity,
    RoanType,
    Genotype,
    Phenotype,
    LOCUS_DEFINITIONS,
)
from big_pig_farm.entities.pigdex import phenotype_key
from big_pig_farm.data.config import BREEDING
from big_pig_farm.entities.guinea_pig import GuineaPig

# Penalty applied to seniors in scoring — large enough that any breeding-age
# pig outranks a senior (max allele score is 10, max uniqueness+het is 15).
_SENIOR_PENALTY = 20.0


class BreedingStrategy(str, Enum):
    """Breeding program strategy for scoring and replacement."""
    TARGET = "target"        # Breed toward specific phenotype targets
    DIVERSITY = "diversity"  # Maximize phenotype variety
    MONEY = "money"          # Maximize sale value + contract fulfillment


class BreedingProgram(BaseModel):
    """Goal-oriented breeding autopilot.

    Set target traits, and the system auto-pairs pigs to maximize
    offspring probability, auto-sells rejects, and manages stock levels.

    Empty set on any axis means "any value OK" for that axis.
    A pig must match every axis that has selections (AND across axes, OR within).
    """

    target_colors: set[BaseColor] = Field(default_factory=set)
    target_patterns: set[Pattern] = Field(default_factory=set)
    target_intensities: set[ColorIntensity] = Field(default_factory=set)
    target_roan: set[RoanType] = Field(default_factory=set)
    keep_carriers: bool = True
    auto_pair: bool = True
    strategy: BreedingStrategy = BreedingStrategy.TARGET
    stock_limit: int = 6
    enabled: bool = False

    @property
    def has_target(self) -> bool:
        """True if any target axis has selections."""
        return bool(
            self.target_colors
            or self.target_patterns
            or self.target_intensities
            or self.target_roan
        )

    def should_auto_pair(self) -> bool:
        """Check if auto-pairing is active."""
        return self.enabled and self.auto_pair


def should_keep_pig(
    program: BreedingProgram,
    pig: GuineaPig,
    has_genetics_lab: bool,
) -> bool:
    """Check if a pig passes the breeding program target filter.

    Returns True if the pig should be kept (not auto-sold).
    Always returns True if the program is disabled.
    """
    if not program.enabled:
        return True

    phenotype = pig.phenotype
    genotype = pig.genotype
    carrier_aware = program.keep_carriers and has_genetics_lab

    # Check each axis - empty set means "keep all" (skip axis)
    if program.target_colors:
        if not _matches_color(phenotype, genotype, program.target_colors, carrier_aware):
            return False

    if program.target_patterns:
        if not _matches_pattern(phenotype, genotype, program.target_patterns, carrier_aware):
            return False

    if program.target_intensities:
        if not _matches_intensity(phenotype, genotype, program.target_intensities, carrier_aware):
            return False

    if program.target_roan:
        if not _matches_roan(phenotype, program.target_roan):
            return False

    return True


def breeding_value(pig: GuineaPig, program: BreedingProgram, has_lab: bool) -> float:
    """Score how useful a pig is for the breeding program.

    Base score is target allele count (0-10 across 5 loci).
    An age bonus (0-5) is added so younger pigs within breeding age
    score higher than older ones with equal genetics.  Seniors (who
    can no longer breed) receive a large penalty so they are culled
    before any breeding-age pig.
    """
    score = 0
    g = pig.genotype

    # Color axis: E, B, and D loci contribute to target colors
    for color in program.target_colors:
        if color in (BaseColor.GOLDEN, BaseColor.CREAM, BaseColor.SAFFRON, BaseColor.SMOKE):
            score += g.e_locus.count("e")
        if color in (BaseColor.CHOCOLATE, BaseColor.CREAM, BaseColor.LILAC, BaseColor.SMOKE):
            score += g.b_locus.count("b")
        if color in (BaseColor.BLACK, BaseColor.BLUE):
            score += g.e_locus.count("E")
            score += g.b_locus.count("B")
        if color in (BaseColor.BLUE, BaseColor.LILAC, BaseColor.SAFFRON, BaseColor.SMOKE):
            score += g.d_locus.count("d")
        if color in (BaseColor.BLACK, BaseColor.CHOCOLATE, BaseColor.GOLDEN, BaseColor.CREAM):
            score += g.d_locus.count("D")

    # Pattern axis: S locus
    for pattern in program.target_patterns:
        if pattern == Pattern.DALMATIAN:
            score += g.s_locus.count("s")
        elif pattern == Pattern.DUTCH:
            # Heterozygous Ss is Dutch, so having 's' helps
            score += g.s_locus.count("s")
        elif pattern == Pattern.SOLID:
            score += g.s_locus.count("S")

    # Intensity axis: C locus
    for intensity in program.target_intensities:
        if intensity == ColorIntensity.HIMALAYAN:
            score += g.c_locus.count("ch")
        elif intensity == ColorIntensity.CHINCHILLA:
            score += g.c_locus.count("ch")
        elif intensity == ColorIntensity.FULL:
            score += g.c_locus.count("C")

    # Roan axis: R locus
    for roan in program.target_roan:
        if roan == RoanType.ROAN:
            score += g.r_locus.count("R")
        elif roan == RoanType.NONE:
            score += g.r_locus.count("r")

    # Seniors can't breed — heavy penalty so they're culled before breeders
    if pig.is_senior:
        score -= _SENIOR_PENALTY

    # Age tiebreaker: younger breeding-age pigs score higher
    remaining = max(0, BREEDING.MAX_AGE_DAYS - pig.age_days)
    age_bonus = (remaining / BREEDING.MAX_AGE_DAYS) * 5.0
    return score + age_bonus


def _matches_color(
    phenotype: Phenotype,
    genotype: Genotype,
    target: set[BaseColor],
    carrier_aware: bool,
) -> bool:
    """Check if pig matches color axis, with optional carrier rescue."""
    if phenotype.base_color in target:
        return True
    if not carrier_aware:
        return False

    # Carrier rescue: pig doesn't show the color but carries allele(s) for it
    for color in target:
        if color == BaseColor.CHOCOLATE and "b" in genotype.b_locus:
            return True
        if color == BaseColor.GOLDEN and "e" in genotype.e_locus:
            return True
        if color == BaseColor.CREAM and "e" in genotype.e_locus and "b" in genotype.b_locus:
            return True
        # Diluted colors: carrier of 'd' allele
        if color in (BaseColor.BLUE, BaseColor.LILAC, BaseColor.SAFFRON, BaseColor.SMOKE):
            if "d" in genotype.d_locus:
                return True
        # BLACK has no carrier state (dominant on both loci)

    return False


def _matches_pattern(
    phenotype: Phenotype,
    genotype: Genotype,
    target: set[Pattern],
    carrier_aware: bool,
) -> bool:
    """Check if pig matches pattern axis, with optional carrier rescue."""
    if phenotype.pattern in target:
        return True
    if not carrier_aware:
        return False

    for pattern in target:
        if pattern in (Pattern.DUTCH, Pattern.DALMATIAN) and "s" in genotype.s_locus:
            return True
        # SOLID has no carrier state (dominant)

    return False


def _matches_intensity(
    phenotype: Phenotype,
    genotype: Genotype,
    target: set[ColorIntensity],
    carrier_aware: bool,
) -> bool:
    """Check if pig matches intensity axis, with optional carrier rescue."""
    if phenotype.intensity in target:
        return True
    if not carrier_aware:
        return False

    for intensity in target:
        if intensity in (ColorIntensity.CHINCHILLA, ColorIntensity.HIMALAYAN) and "ch" in genotype.c_locus:
            return True
        # FULL has no carrier state (dominant)

    return False


def _matches_roan(
    phenotype: Phenotype,
    target: set[RoanType],
) -> bool:
    """Check if pig matches roan axis. No carrier rescue for roan."""
    return phenotype.roan in target


def _heterozygosity_count(genotype: Genotype) -> int:
    """Count how many loci are heterozygous (0-5).

    A pig heterozygous at more loci produces more varied offspring.
    """
    count = 0
    for locus_name, dominant, recessive in LOCUS_DEFINITIONS:
        locus = getattr(genotype, locus_name)
        if dominant in locus and recessive in locus:
            count += 1
    return count


def diversity_value(pig: GuineaPig, all_pigs: list[GuineaPig]) -> float:
    """Score a pig's contribution to phenotype diversity.

    Components:
    - Uniqueness (0-10): 10 / count_of_pigs_sharing_phenotype
    - Heterozygosity bonus (0-5): heterozygous loci count
    - Age tiebreaker (0-3): younger pigs break ties
    - Senior penalty (-20): seniors can't breed, cull them first
    """
    key = phenotype_key(pig.phenotype)
    same_count = sum(1 for p in all_pigs if phenotype_key(p.phenotype) == key)
    uniqueness = 10.0 / same_count
    het_bonus = float(_heterozygosity_count(pig.genotype))
    remaining = max(0, BREEDING.MAX_AGE_DAYS - pig.age_days)
    age_bonus = (remaining / BREEDING.MAX_AGE_DAYS) * 3.0
    score = uniqueness + het_bonus + age_bonus
    if pig.is_senior:
        score -= _SENIOR_PENALTY
    return score


def money_value(pig: GuineaPig, program: BreedingProgram, has_lab: bool, game_state) -> float:
    """Score a pig's breeding potential for producing high-value offspring.

    Components:
    - Rarity allele score: weight alleles by how much they contribute to rarity
    - Contract alignment bonus: reward for carrying alleles toward active contracts
    - Age tiebreaker (0-5): younger pigs score higher
    - Senior penalty (-20): seniors can't breed
    """
    g = pig.genotype
    score = 0.0

    # Rarity allele scores — rarer alleles are more valuable
    score += g.c_locus.count("ch") * 3.0   # Himalayan (ch/ch) worth most
    score += g.s_locus.count("s") * 2.0    # Dalmatian (s/s) is rare
    score += g.r_locus.count("R") * 2.0    # Roan (R/r) is rare
    score += g.b_locus.count("b") * 1.0    # Chocolate/Cream contributor
    score += g.e_locus.count("e") * 0.5    # Cream needs both e and b

    # Contract alignment bonus
    if hasattr(game_state, "contract_board"):
        for contract in game_state.contract_board.active_contracts:
            if contract.fulfilled:
                continue
            weight = contract.reward / 100.0
            allele_hits = _contract_allele_hits(g, contract)
            score += allele_hits * weight

    # Senior penalty
    if pig.is_senior:
        score -= _SENIOR_PENALTY

    # Age tiebreaker
    remaining = max(0, BREEDING.MAX_AGE_DAYS - pig.age_days)
    age_bonus = (remaining / BREEDING.MAX_AGE_DAYS) * 5.0
    return score + age_bonus


def _contract_allele_hits(genotype: Genotype, contract) -> int:
    """Count how many alleles a pig carries toward a contract's requirements."""
    hits = 0
    if contract.required_color:
        color = contract.required_color
        if color in (BaseColor.GOLDEN, BaseColor.CREAM, BaseColor.SAFFRON, BaseColor.SMOKE):
            hits += genotype.e_locus.count("e")
        if color in (BaseColor.CHOCOLATE, BaseColor.CREAM, BaseColor.LILAC, BaseColor.SMOKE):
            hits += genotype.b_locus.count("b")
        if color in (BaseColor.BLACK, BaseColor.BLUE):
            hits += genotype.e_locus.count("E")
            hits += genotype.b_locus.count("B")
        if color in (BaseColor.BLUE, BaseColor.LILAC, BaseColor.SAFFRON, BaseColor.SMOKE):
            hits += genotype.d_locus.count("d")
    if contract.required_pattern:
        pattern = contract.required_pattern
        if pattern == Pattern.DALMATIAN:
            hits += genotype.s_locus.count("s")
        elif pattern == Pattern.DUTCH:
            hits += genotype.s_locus.count("s")
        elif pattern == Pattern.SOLID:
            hits += genotype.s_locus.count("S")
    if contract.required_intensity:
        intensity = contract.required_intensity
        if intensity in (ColorIntensity.HIMALAYAN, ColorIntensity.CHINCHILLA):
            hits += genotype.c_locus.count("ch")
        elif intensity == ColorIntensity.FULL:
            hits += genotype.c_locus.count("C")
    if contract.required_roan:
        roan = contract.required_roan
        if roan == RoanType.ROAN:
            hits += genotype.r_locus.count("R")
        elif roan == RoanType.NONE:
            hits += genotype.r_locus.count("r")
    return hits
