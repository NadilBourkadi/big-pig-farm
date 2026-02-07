"""Tests for the genetics system."""

import pytest
from big_pig_farm.entities.genetics import (
    Genotype,
    Phenotype,
    BaseColor,
    Pattern,
    Rarity,
    calculate_phenotype,
    breed,
    inherit_allele,
)


class TestGenotype:
    """Tests for Genotype class."""

    def test_random_genotype(self):
        """Test generating a random genotype."""
        genotype = Genotype.random()
        assert genotype.e_locus is not None
        assert genotype.b_locus is not None
        assert genotype.s_locus is not None
        assert genotype.c_locus is not None
        assert genotype.r_locus is not None

    def test_random_common_genotype(self):
        """Test generating a common genotype."""
        genotype = Genotype.random_common()
        # Common genotypes should have solid pattern
        assert genotype.s_locus == ("S", "S")
        # And full color
        assert genotype.c_locus == ("C", "C")

    def test_has_dominant(self):
        """Test checking for dominant alleles."""
        genotype = Genotype(
            e_locus=("E", "e"),
            b_locus=("b", "b"),
            s_locus=("S", "S"),
            c_locus=("C", "C"),
            r_locus=("r", "r"),
        )
        assert genotype.has_dominant(genotype.e_locus, "E") is True
        assert genotype.has_dominant(genotype.b_locus, "B") is False

    def test_is_homozygous_recessive(self):
        """Test checking for homozygous recessive."""
        genotype = Genotype(
            e_locus=("e", "e"),
            b_locus=("B", "b"),
            s_locus=("S", "S"),
            c_locus=("C", "C"),
            r_locus=("r", "r"),
        )
        assert genotype.is_homozygous_recessive(genotype.e_locus, "e") is True
        assert genotype.is_homozygous_recessive(genotype.b_locus, "b") is False


class TestPhenotype:
    """Tests for phenotype calculation."""

    def test_black_phenotype(self):
        """Test black color phenotype."""
        genotype = Genotype(
            e_locus=("E", "E"),
            b_locus=("B", "B"),
            s_locus=("S", "S"),
            c_locus=("C", "C"),
            r_locus=("r", "r"),
        )
        phenotype = calculate_phenotype(genotype)
        assert phenotype.base_color == BaseColor.BLACK
        assert phenotype.pattern == Pattern.SOLID

    def test_chocolate_phenotype(self):
        """Test chocolate color phenotype."""
        genotype = Genotype(
            e_locus=("E", "E"),
            b_locus=("b", "b"),
            s_locus=("S", "S"),
            c_locus=("C", "C"),
            r_locus=("r", "r"),
        )
        phenotype = calculate_phenotype(genotype)
        assert phenotype.base_color == BaseColor.CHOCOLATE

    def test_golden_phenotype(self):
        """Test golden color phenotype."""
        genotype = Genotype(
            e_locus=("e", "e"),
            b_locus=("B", "B"),
            s_locus=("S", "S"),
            c_locus=("C", "C"),
            r_locus=("r", "r"),
        )
        phenotype = calculate_phenotype(genotype)
        assert phenotype.base_color == BaseColor.GOLDEN

    def test_dalmatian_pattern(self):
        """Test dalmatian pattern phenotype."""
        genotype = Genotype(
            e_locus=("E", "E"),
            b_locus=("B", "B"),
            s_locus=("s", "s"),
            c_locus=("C", "C"),
            r_locus=("r", "r"),
        )
        phenotype = calculate_phenotype(genotype)
        assert phenotype.pattern == Pattern.DALMATIAN

    def test_dutch_pattern(self):
        """Test Dutch pattern phenotype."""
        genotype = Genotype(
            e_locus=("E", "E"),
            b_locus=("B", "B"),
            s_locus=("S", "s"),
            c_locus=("C", "C"),
            r_locus=("r", "r"),
        )
        phenotype = calculate_phenotype(genotype)
        assert phenotype.pattern == Pattern.DUTCH

    def test_rarity_calculation(self):
        """Test rarity tier calculation."""
        # Common: solid black
        common_genotype = Genotype(
            e_locus=("E", "E"),
            b_locus=("B", "B"),
            s_locus=("S", "S"),
            c_locus=("C", "C"),
            r_locus=("r", "r"),
        )
        common_phenotype = calculate_phenotype(common_genotype)
        assert common_phenotype.rarity == Rarity.COMMON

        # Rare: dalmatian pattern
        rare_genotype = Genotype(
            e_locus=("E", "E"),
            b_locus=("B", "B"),
            s_locus=("s", "s"),
            c_locus=("C", "C"),
            r_locus=("r", "r"),
        )
        rare_phenotype = calculate_phenotype(rare_genotype)
        assert rare_phenotype.rarity in (Rarity.RARE, Rarity.UNCOMMON)


class TestBreeding:
    """Tests for breeding mechanics."""

    def test_inherit_allele(self):
        """Test allele inheritance."""
        parent1 = ("E", "e")
        parent2 = ("E", "E")

        # Should get one allele from each parent
        for _ in range(10):
            child = inherit_allele(parent1, parent2)
            assert len(child) == 2
            assert child[0] in ("E", "e")
            assert child[1] == "E"

    def test_breed_produces_valid_genotype(self):
        """Test that breeding produces valid offspring."""
        parent1 = Genotype.random()
        parent2 = Genotype.random()

        for _ in range(10):
            result = breed(parent1, parent2)
            child = result.genotype
            assert child.e_locus is not None
            assert child.b_locus is not None
            # Should be able to calculate phenotype
            phenotype = calculate_phenotype(child)
            assert phenotype is not None

    def test_lethal_roan_reroll(self):
        """Test that lethal RR combination is re-rolled."""
        # Two roan parents
        parent1 = Genotype(
            e_locus=("E", "E"),
            b_locus=("B", "B"),
            s_locus=("S", "S"),
            c_locus=("C", "C"),
            r_locus=("R", "r"),
        )
        parent2 = Genotype(
            e_locus=("E", "E"),
            b_locus=("B", "B"),
            s_locus=("S", "S"),
            c_locus=("C", "C"),
            r_locus=("R", "r"),
        )

        # Should never produce RR offspring
        for _ in range(100):
            result = breed(parent1, parent2)
            assert result.genotype.r_locus != ("R", "R"), "Lethal RR should be re-rolled"
