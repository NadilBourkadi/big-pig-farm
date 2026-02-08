"""Breeding filter - auto-mark newborns that don't match trait preferences."""

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


class BreedingFilter(BaseModel):
    """Trait-based auto-sell rules for newborn pigs.

    Empty set on any axis means "keep all" for that axis.
    A pig must match every axis that has selections (AND across axes, OR within).
    """

    keep_colors: set[BaseColor] = Field(default_factory=set)
    keep_patterns: set[Pattern] = Field(default_factory=set)
    keep_intensities: set[ColorIntensity] = Field(default_factory=set)
    keep_roan: set[RoanType] = Field(default_factory=set)
    carrier_aware: bool = False
    enabled: bool = False


def should_keep_pig(
    breeding_filter: BreedingFilter,
    pig: GuineaPig,
    has_genetics_lab: bool,
) -> bool:
    """Check if a pig passes the breeding filter.

    Returns True if the pig should be kept (not auto-sold).
    Always returns True if the filter is disabled.
    """
    if not breeding_filter.enabled:
        return True

    phenotype = pig.phenotype
    genotype = pig.genotype
    carrier_aware = breeding_filter.carrier_aware and has_genetics_lab

    # Check each axis - empty set means "keep all" (skip axis)
    if breeding_filter.keep_colors:
        if not _matches_color(phenotype, genotype, breeding_filter.keep_colors, carrier_aware):
            return False

    if breeding_filter.keep_patterns:
        if not _matches_pattern(phenotype, genotype, breeding_filter.keep_patterns, carrier_aware):
            return False

    if breeding_filter.keep_intensities:
        if not _matches_intensity(phenotype, genotype, breeding_filter.keep_intensities, carrier_aware):
            return False

    if breeding_filter.keep_roan:
        if not _matches_roan(phenotype, breeding_filter.keep_roan):
            return False

    return True


def _matches_color(
    phenotype: Phenotype,
    genotype: Genotype,
    keep: set[BaseColor],
    carrier_aware: bool,
) -> bool:
    """Check if pig matches color axis, with optional carrier rescue."""
    if phenotype.base_color in keep:
        return True
    if not carrier_aware:
        return False

    # Carrier rescue: pig doesn't show the color but carries allele(s) for it
    for color in keep:
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
    keep: set[Pattern],
    carrier_aware: bool,
) -> bool:
    """Check if pig matches pattern axis, with optional carrier rescue."""
    if phenotype.pattern in keep:
        return True
    if not carrier_aware:
        return False

    for pattern in keep:
        if pattern in (Pattern.DUTCH, Pattern.DALMATIAN) and "s" in genotype.s_locus:
            return True
        # SOLID has no carrier state (dominant)

    return False


def _matches_intensity(
    phenotype: Phenotype,
    genotype: Genotype,
    keep: set[ColorIntensity],
    carrier_aware: bool,
) -> bool:
    """Check if pig matches intensity axis, with optional carrier rescue."""
    if phenotype.intensity in keep:
        return True
    if not carrier_aware:
        return False

    for intensity in keep:
        if intensity in (ColorIntensity.CHINCHILLA, ColorIntensity.HIMALAYAN) and "ch" in genotype.c_locus:
            return True
        # FULL has no carrier state (dominant)

    return False


def _matches_roan(
    phenotype: Phenotype,
    keep: set[RoanType],
) -> bool:
    """Check if pig matches roan axis. No carrier rescue for roan."""
    return phenotype.roan in keep
