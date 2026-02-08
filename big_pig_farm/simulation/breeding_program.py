"""Breeding program - goal-oriented autopilot for selective breeding."""

from pydantic import BaseModel, Field

from big_pig_farm.entities.genetics import (
    BaseColor,
    Pattern,
    ColorIntensity,
    RoanType,
    Genotype,
    Phenotype,
)
from big_pig_farm.entities.guinea_pig import GuineaPig


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


def breeding_value(pig: GuineaPig, program: BreedingProgram, has_lab: bool) -> int:
    """Score how useful a pig's genotype is for the breeding program.

    Counts target alleles the pig carries (0-10 across 5 loci).
    Higher = more useful for breeding toward the target.
    """
    score = 0
    g = pig.genotype

    # Color axis: E and B loci contribute to target colors
    for color in program.target_colors:
        if color == BaseColor.GOLDEN or color == BaseColor.CREAM:
            # Want recessive e alleles
            score += g.e_locus.count("e")
        if color == BaseColor.CHOCOLATE or color == BaseColor.CREAM:
            # Want recessive b alleles
            score += g.b_locus.count("b")
        if color == BaseColor.BLACK:
            # Want dominant E and B
            score += g.e_locus.count("E")
            score += g.b_locus.count("B")

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

    return score


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
