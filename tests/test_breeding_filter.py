"""Tests for the breeding filter system."""

import pytest

from big_pig_farm.entities.guinea_pig import GuineaPig, Gender, Position
from big_pig_farm.entities.genetics import (
    Genotype,
    BaseColor,
    Pattern,
    ColorIntensity,
    RoanType,
    calculate_phenotype,
)
from big_pig_farm.simulation.breeding_filter import BreedingFilter, should_keep_pig


def _make_pig_with_genotype(**loci) -> GuineaPig:
    """Create a pig with specific locus values.

    Pass keyword args like e_locus=("E", "e"), b_locus=("b", "b"), etc.
    Unspecified loci default to homozygous dominant.
    """
    defaults = {
        "e_locus": ("E", "E"),
        "b_locus": ("B", "B"),
        "s_locus": ("S", "S"),
        "c_locus": ("C", "C"),
        "r_locus": ("r", "r"),
    }
    defaults.update(loci)
    genotype = Genotype(**defaults)
    return GuineaPig.create(
        name="Test",
        gender=Gender.MALE,
        genotype=genotype,
        position=Position(x=5.0, y=5.0),
    )


class TestDisabledFilter:
    """A disabled filter should keep everything."""

    def test_disabled_keeps_all(self):
        f = BreedingFilter(enabled=False, keep_colors={BaseColor.CHOCOLATE})
        pig = _make_pig_with_genotype()  # Black, Solid, Full, no Roan
        assert should_keep_pig(f, pig, has_genetics_lab=False)

    def test_default_filter_keeps_all(self):
        f = BreedingFilter()
        pig = _make_pig_with_genotype()
        assert should_keep_pig(f, pig, has_genetics_lab=False)


class TestEmptyAxes:
    """Empty set on an axis means 'don't filter that axis'."""

    def test_empty_filter_enabled_keeps_all(self):
        f = BreedingFilter(enabled=True)
        pig = _make_pig_with_genotype()
        assert should_keep_pig(f, pig, has_genetics_lab=False)

    def test_empty_colors_keeps_any_color(self):
        f = BreedingFilter(enabled=True, keep_patterns={Pattern.SOLID})
        # Chocolate pig with Solid pattern
        pig = _make_pig_with_genotype(e_locus=("E", "E"), b_locus=("b", "b"))
        assert should_keep_pig(f, pig, has_genetics_lab=False)


class TestSingleAxisFiltering:
    """Test filtering on individual axes."""

    def test_color_match_keeps(self):
        f = BreedingFilter(enabled=True, keep_colors={BaseColor.CHOCOLATE})
        pig = _make_pig_with_genotype(b_locus=("b", "b"))  # Chocolate
        assert should_keep_pig(f, pig, has_genetics_lab=False)

    def test_color_mismatch_marks(self):
        f = BreedingFilter(enabled=True, keep_colors={BaseColor.CHOCOLATE})
        pig = _make_pig_with_genotype()  # Black
        assert not should_keep_pig(f, pig, has_genetics_lab=False)

    def test_multiple_colors_or_logic(self):
        f = BreedingFilter(enabled=True, keep_colors={BaseColor.CHOCOLATE, BaseColor.GOLDEN})
        black_pig = _make_pig_with_genotype()
        choc_pig = _make_pig_with_genotype(b_locus=("b", "b"))
        golden_pig = _make_pig_with_genotype(e_locus=("e", "e"))
        assert not should_keep_pig(f, black_pig, has_genetics_lab=False)
        assert should_keep_pig(f, choc_pig, has_genetics_lab=False)
        assert should_keep_pig(f, golden_pig, has_genetics_lab=False)

    def test_pattern_match_keeps(self):
        f = BreedingFilter(enabled=True, keep_patterns={Pattern.DALMATIAN})
        pig = _make_pig_with_genotype(s_locus=("s", "s"))  # Dalmatian
        assert should_keep_pig(f, pig, has_genetics_lab=False)

    def test_pattern_mismatch_marks(self):
        f = BreedingFilter(enabled=True, keep_patterns={Pattern.DALMATIAN})
        pig = _make_pig_with_genotype(s_locus=("S", "S"))  # Solid
        assert not should_keep_pig(f, pig, has_genetics_lab=False)

    def test_intensity_match_keeps(self):
        f = BreedingFilter(enabled=True, keep_intensities={ColorIntensity.HIMALAYAN})
        pig = _make_pig_with_genotype(c_locus=("ch", "ch"))  # Himalayan
        assert should_keep_pig(f, pig, has_genetics_lab=False)

    def test_intensity_mismatch_marks(self):
        f = BreedingFilter(enabled=True, keep_intensities={ColorIntensity.HIMALAYAN})
        pig = _make_pig_with_genotype(c_locus=("C", "C"))  # Full
        assert not should_keep_pig(f, pig, has_genetics_lab=False)

    def test_roan_match_keeps(self):
        f = BreedingFilter(enabled=True, keep_roan={RoanType.ROAN})
        pig = _make_pig_with_genotype(r_locus=("R", "r"))  # Roan
        assert should_keep_pig(f, pig, has_genetics_lab=False)

    def test_roan_mismatch_marks(self):
        f = BreedingFilter(enabled=True, keep_roan={RoanType.ROAN})
        pig = _make_pig_with_genotype(r_locus=("r", "r"))  # No roan
        assert not should_keep_pig(f, pig, has_genetics_lab=False)


class TestMultiAxisAndLogic:
    """Multiple axes must ALL match (AND logic)."""

    def test_two_axes_both_match(self):
        f = BreedingFilter(
            enabled=True,
            keep_colors={BaseColor.CHOCOLATE},
            keep_patterns={Pattern.DALMATIAN},
        )
        pig = _make_pig_with_genotype(b_locus=("b", "b"), s_locus=("s", "s"))
        assert should_keep_pig(f, pig, has_genetics_lab=False)

    def test_two_axes_one_fails(self):
        f = BreedingFilter(
            enabled=True,
            keep_colors={BaseColor.CHOCOLATE},
            keep_patterns={Pattern.DALMATIAN},
        )
        # Chocolate but Solid (pattern fails)
        pig = _make_pig_with_genotype(b_locus=("b", "b"), s_locus=("S", "S"))
        assert not should_keep_pig(f, pig, has_genetics_lab=False)

    def test_all_four_axes(self):
        f = BreedingFilter(
            enabled=True,
            keep_colors={BaseColor.GOLDEN},
            keep_patterns={Pattern.DUTCH},
            keep_intensities={ColorIntensity.HIMALAYAN},
            keep_roan={RoanType.ROAN},
        )
        # Golden, Dutch, Himalayan, Roan
        pig = _make_pig_with_genotype(
            e_locus=("e", "e"),
            b_locus=("B", "B"),
            s_locus=("S", "s"),
            c_locus=("ch", "ch"),
            r_locus=("R", "r"),
        )
        assert should_keep_pig(f, pig, has_genetics_lab=False)


class TestCarrierAware:
    """Carrier-aware mode rescues heterozygous pigs when Genetics Lab exists."""

    def test_carrier_aware_requires_genetics_lab(self):
        f = BreedingFilter(
            enabled=True,
            keep_colors={BaseColor.CHOCOLATE},
            carrier_aware=True,
        )
        # Black pig carrying b allele (Bb)
        pig = _make_pig_with_genotype(b_locus=("B", "b"))
        # Without lab: not kept
        assert not should_keep_pig(f, pig, has_genetics_lab=False)

    def test_carrier_aware_with_lab_keeps_carrier(self):
        f = BreedingFilter(
            enabled=True,
            keep_colors={BaseColor.CHOCOLATE},
            carrier_aware=True,
        )
        pig = _make_pig_with_genotype(b_locus=("B", "b"))
        assert should_keep_pig(f, pig, has_genetics_lab=True)

    def test_carrier_aware_golden(self):
        f = BreedingFilter(
            enabled=True,
            keep_colors={BaseColor.GOLDEN},
            carrier_aware=True,
        )
        # Black pig carrying e allele (Ee)
        pig = _make_pig_with_genotype(e_locus=("E", "e"))
        assert should_keep_pig(f, pig, has_genetics_lab=True)

    def test_carrier_aware_light_golden(self):
        f = BreedingFilter(
            enabled=True,
            keep_colors={BaseColor.LIGHT_GOLDEN},
            carrier_aware=True,
        )
        # Black pig carrying both e and b
        pig = _make_pig_with_genotype(e_locus=("E", "e"), b_locus=("B", "b"))
        assert should_keep_pig(f, pig, has_genetics_lab=True)

    def test_carrier_aware_light_golden_needs_both_alleles(self):
        f = BreedingFilter(
            enabled=True,
            keep_colors={BaseColor.LIGHT_GOLDEN},
            carrier_aware=True,
        )
        # Only carries e, not b → not rescued for light golden
        pig = _make_pig_with_genotype(e_locus=("E", "e"), b_locus=("B", "B"))
        assert not should_keep_pig(f, pig, has_genetics_lab=True)

    def test_carrier_aware_pattern_dutch(self):
        f = BreedingFilter(
            enabled=True,
            keep_patterns={Pattern.DUTCH},
            carrier_aware=True,
        )
        # Solid pig carrying s allele (Ss) → already Dutch phenotype, trivially kept
        # Use SS pig carrying nothing
        pig = _make_pig_with_genotype(s_locus=("S", "S"))
        assert not should_keep_pig(f, pig, has_genetics_lab=True)

    def test_carrier_aware_pattern_dalmatian_rescued(self):
        f = BreedingFilter(
            enabled=True,
            keep_patterns={Pattern.DALMATIAN},
            carrier_aware=True,
        )
        # Dutch pig (Ss) carries s allele → rescued for dalmatian interest
        pig = _make_pig_with_genotype(s_locus=("S", "s"))
        assert should_keep_pig(f, pig, has_genetics_lab=True)

    def test_carrier_aware_intensity_himalayan(self):
        f = BreedingFilter(
            enabled=True,
            keep_intensities={ColorIntensity.HIMALAYAN},
            carrier_aware=True,
        )
        # Chinchilla pig (C/ch) carries ch allele → rescued
        pig = _make_pig_with_genotype(c_locus=("C", "ch"))
        assert should_keep_pig(f, pig, has_genetics_lab=True)

    def test_carrier_aware_no_rescue_for_dominant_traits(self):
        """Black (dominant) and Solid (dominant) have no carrier state."""
        f = BreedingFilter(
            enabled=True,
            keep_colors={BaseColor.BLACK},
            carrier_aware=True,
        )
        # Chocolate pig (bb) — no way to "carry" black
        pig = _make_pig_with_genotype(e_locus=("E", "E"), b_locus=("b", "b"))
        assert not should_keep_pig(f, pig, has_genetics_lab=True)

    def test_carrier_aware_roan_no_rescue(self):
        """Roan has no carrier rescue (dominant trait)."""
        f = BreedingFilter(
            enabled=True,
            keep_roan={RoanType.ROAN},
            carrier_aware=True,
        )
        pig = _make_pig_with_genotype(r_locus=("r", "r"))
        assert not should_keep_pig(f, pig, has_genetics_lab=True)
