"""Tests for directional biome mutations and color affinity."""

import pytest

from big_pig_farm.data.config import BIOME, TIME
from big_pig_farm.entities.biomes import (
    BIOME_SIGNATURE_COLORS,
    BIOMES,
    BiomeType,
)
from big_pig_farm.entities.genetics import (
    BaseColor,
    Genotype,
    breed,
    calculate_phenotype,
    mutate_locus_directional,
)
from big_pig_farm.entities.guinea_pig import Gender, GuineaPig, Position
from big_pig_farm.simulation.acclimation import update_acclimation


class TestMutateLocusDirectional:
    """Tests for the directional mutation function."""

    def test_pushes_toward_target(self):
        """Directional mutation only pushes toward the target allele."""
        mutations_toward = 0
        trials = 1000
        for _ in range(trials):
            new_locus, did_mutate = mutate_locus_directional(
                ("B", "B"), "b", 1.0,  # 100% rate, target = recessive b
            )
            if did_mutate:
                mutations_toward += 1
                # Must have at least one 'b' now
                assert "b" in new_locus

        # With 100% rate and BB locus, every roll should hit a dominant allele
        assert mutations_toward == trials

    def test_never_pushes_away_from_target(self):
        """If locus is already at target, mutation is wasted (no flip away)."""
        for _ in range(500):
            new_locus, did_mutate = mutate_locus_directional(
                ("b", "b"), "b", 1.0,  # Already homozygous target
            )
            # Both alleles match target, so mutation should always be wasted
            assert not did_mutate
            assert new_locus == ("b", "b")

    def test_heterozygous_can_mutate(self):
        """Heterozygous locus has 50% chance per roll of hitting the non-target allele."""
        mutated_count = 0
        for _ in range(1000):
            new_locus, did_mutate = mutate_locus_directional(
                ("B", "b"), "b", 1.0,
            )
            if did_mutate:
                mutated_count += 1
                # The B should have been replaced with b
                assert new_locus == ("b", "b")

        # ~50% of rolls should hit the B position
        assert 350 < mutated_count < 650

    def test_respects_rate(self):
        """Zero rate should never mutate."""
        for _ in range(100):
            new_locus, did_mutate = mutate_locus_directional(
                ("B", "B"), "b", 0.0,
            )
            assert not did_mutate
            assert new_locus == ("B", "B")

    def test_rr_lethal_guard_in_breed(self):
        """Directional mutation toward R should not create R/R."""
        # Two non-roan parents with r/r, directional push toward R
        parent = Genotype(
            e_locus=("E", "E"), b_locus=("B", "B"),
            s_locus=("S", "S"), c_locus=("C", "C"),
            r_locus=("R", "r"), d_locus=("D", "D"),
        )
        for _ in range(200):
            result = breed(
                parent, parent,
                directional_targets={"r_locus": "R"},
                directional_rate=1.0,
            )
            assert result.genotype.r_locus != ("R", "R")


class TestBreedDirectional:
    """Tests for breed() with directional targets."""

    def test_directional_targets_affect_color_loci(self):
        """Color loci should mutate directionally while others mutate randomly."""
        # Wild-type parents (all dominant)
        parent = Genotype(
            e_locus=("E", "E"), b_locus=("B", "B"),
            s_locus=("S", "S"), c_locus=("C", "C"),
            r_locus=("r", "r"), d_locus=("D", "D"),
        )
        # Burrow directional targets: E, b, D (push toward chocolate)
        targets = {"e_locus": "E", "b_locus": "b", "d_locus": "D"}

        b_mutations = 0
        for _ in range(500):
            result = breed(
                parent, parent,
                directional_targets=targets,
                directional_rate=0.5,  # High rate for statistical significance
            )
            # Check if b_locus got pushed toward recessive
            if "b" in result.genotype.b_locus:
                b_mutations += 1

        # With 50% directional rate and BB parents, ~25% of offspring should
        # carry at least one b allele (rate * P(hit dominant position))
        assert b_mutations > 50  # Should be well above zero

    def test_non_targeted_loci_use_base_rate(self):
        """Loci without directional targets should use the base mutation rate."""
        parent = Genotype(
            e_locus=("E", "E"), b_locus=("B", "B"),
            s_locus=("S", "S"), c_locus=("C", "C"),
            r_locus=("r", "r"), d_locus=("D", "D"),
        )
        # Only target color loci; s_locus should use base rate
        targets = {"e_locus": "e", "b_locus": "b", "d_locus": "d"}

        s_mutations = 0
        for _ in range(2000):
            result = breed(
                parent, parent,
                mutation_rate=0.02,
                directional_targets=targets,
                directional_rate=0.5,
            )
            if "s" in result.genotype.s_locus:
                s_mutations += 1

        # s_locus should mutate at ~2% (base rate), not 50%
        # With 2000 trials at 2%, expect ~40 mutations
        assert s_mutations < 150  # Well below directional rate levels

    def test_locus_rates_and_directional_coexist(self):
        """Per-locus rate overrides apply to non-directional loci alongside directional targets."""
        parent = Genotype(
            e_locus=("E", "E"), b_locus=("B", "B"),
            s_locus=("S", "S"), c_locus=("C", "C"),
            r_locus=("r", "r"), d_locus=("D", "D"),
        )
        # Directional for color loci, boosted rate for s_locus
        result_mutations = 0
        for _ in range(1000):
            result = breed(
                parent, parent,
                mutation_rate=0.02,
                locus_rates={"s_locus": 0.10},  # 10% boost on spotting
                directional_targets={"e_locus": "e"},
                directional_rate=0.06,
            )
            if "s" in result.genotype.s_locus:
                result_mutations += 1

        # Should see significantly more s_locus mutations than base 2%
        assert result_mutations > 30


class TestBiomeSignatureColors:
    """Tests for biome signature color mappings."""

    def test_all_biomes_have_signature_color(self):
        """Every biome should define a signature color."""
        for biome_type, info in BIOMES.items():
            assert info.signature_color is not None, f"{biome_type} missing signature_color"

    def test_all_biomes_have_directional_alleles(self):
        """Every biome should define directional alleles for e/b/d loci."""
        for biome_type, info in BIOMES.items():
            assert "e_locus" in info.directional_alleles, f"{biome_type} missing e_locus"
            assert "b_locus" in info.directional_alleles, f"{biome_type} missing b_locus"
            assert "d_locus" in info.directional_alleles, f"{biome_type} missing d_locus"

    def test_signature_colors_unique(self):
        """Each biome should have a distinct signature color."""
        colors = [info.signature_color for info in BIOMES.values()]
        assert len(colors) == len(set(colors))

    def test_lookup_dict_matches_biomes(self):
        """BIOME_SIGNATURE_COLORS should match BIOMES data."""
        for biome_type, info in BIOMES.items():
            assert BIOME_SIGNATURE_COLORS[biome_type.value] == info.signature_color

    def test_no_color_loci_in_mutation_boost(self):
        """Color loci (e/b/d) should not appear in mutation_boost_loci."""
        color_loci = {"e_locus", "b_locus", "d_locus"}
        for biome_type, info in BIOMES.items():
            overlap = color_loci & set(info.mutation_boost_loci.keys())
            assert not overlap, f"{biome_type} has color loci in mutation_boost_loci: {overlap}"

    @pytest.mark.parametrize("biome,expected_color", [
        (BiomeType.MEADOW, BaseColor.BLACK),
        (BiomeType.BURROW, BaseColor.CHOCOLATE),
        (BiomeType.GARDEN, BaseColor.GOLDEN),
        (BiomeType.TROPICAL, BaseColor.CREAM),
        (BiomeType.ALPINE, BaseColor.BLUE),
        (BiomeType.CRYSTAL, BaseColor.LILAC),
        (BiomeType.WILDFLOWER, BaseColor.SAFFRON),
        (BiomeType.SANCTUARY, BaseColor.SMOKE),
    ])
    def test_biome_color_mapping(self, biome, expected_color):
        """Each biome maps to its expected signature color."""
        assert BIOMES[biome].signature_color == expected_color


class TestBiomeColorFrequency:
    """Integration test: breeding in a biome should produce its signature color more often."""

    def test_burrow_produces_more_chocolate(self):
        """Breeding in Burrow (chocolate) should yield more chocolate than in Meadow."""
        # Wild-type parents — heterozygous at b_locus so chocolate is possible
        parent = Genotype(
            e_locus=("E", "E"), b_locus=("B", "b"),
            s_locus=("S", "S"), c_locus=("C", "C"),
            r_locus=("r", "r"), d_locus=("D", "D"),
        )

        burrow_info = BIOMES[BiomeType.BURROW]
        meadow_info = BIOMES[BiomeType.MEADOW]

        def count_color(targets, rate, trials=2000):
            chocolate = 0
            for _ in range(trials):
                result = breed(
                    parent, parent,
                    directional_targets=targets,
                    directional_rate=rate,
                )
                phenotype = calculate_phenotype(result.genotype)
                if phenotype.base_color == BaseColor.CHOCOLATE:
                    chocolate += 1
            return chocolate

        burrow_chocolate = count_color(burrow_info.directional_alleles, 0.06)
        meadow_chocolate = count_color(meadow_info.directional_alleles, 0.06)

        # Burrow pushes toward b (chocolate), Meadow pushes toward B (black)
        assert burrow_chocolate > meadow_chocolate


class TestColorMatchAcclimation:
    """Tests for faster acclimation when pig color matches biome."""

    _ACCLIMATION_HOURS = BIOME.ACCLIMATION_DAYS * TIME.GAME_HOURS_PER_DAY

    def _make_pig(self, base_color: BaseColor, preferred_biome: str = "meadow") -> GuineaPig:
        """Create a pig with a specific base color."""
        # Build a genotype that produces the desired base color
        color_genotypes = {
            BaseColor.BLACK: {"e_locus": ("E", "E"), "b_locus": ("B", "B"), "d_locus": ("D", "D")},
            BaseColor.BLUE: {"e_locus": ("E", "E"), "b_locus": ("B", "B"), "d_locus": ("d", "d")},
            BaseColor.GOLDEN: {"e_locus": ("e", "e"), "b_locus": ("B", "B"), "d_locus": ("D", "D")},
        }
        loci = color_genotypes[base_color]
        genotype = Genotype(
            e_locus=loci["e_locus"], b_locus=loci["b_locus"],
            s_locus=("S", "S"), c_locus=("C", "C"),
            r_locus=("r", "r"), d_locus=loci["d_locus"],
        )
        pig = GuineaPig.create(
            name="Test", gender=Gender.MALE, position=Position(x=5.0, y=5.0),
            age_days=5.0, genotype=genotype,
        )
        pig.preferred_biome = preferred_biome
        return pig

    def test_matching_color_acclimate_faster(self):
        """A blue pig in Alpine (signature=blue) should acclimate in half the time."""
        pig = self._make_pig(BaseColor.BLUE, preferred_biome="meadow")
        half_threshold = self._ACCLIMATION_HOURS * BIOME.COLOR_MATCH_ACCLIMATION_MULTIPLIER

        # Advance just past the reduced threshold
        pig.acclimation_timer = half_threshold - 0.5
        pig.acclimating_biome = "alpine"
        update_acclimation(pig, "alpine", 1.0)

        assert pig.preferred_biome == "alpine"

    def test_non_matching_color_normal_speed(self):
        """A golden pig in Alpine should acclimate at normal speed."""
        pig = self._make_pig(BaseColor.GOLDEN, preferred_biome="meadow")
        half_threshold = self._ACCLIMATION_HOURS * BIOME.COLOR_MATCH_ACCLIMATION_MULTIPLIER

        # At the reduced threshold, a non-matching pig should NOT have acclimated
        pig.acclimation_timer = half_threshold - 0.5
        pig.acclimating_biome = "alpine"
        update_acclimation(pig, "alpine", 1.0)

        assert pig.preferred_biome == "meadow"  # Still original

    def test_non_matching_acclimates_at_full_threshold(self):
        """A non-matching pig eventually acclimates at the full threshold."""
        pig = self._make_pig(BaseColor.GOLDEN, preferred_biome="meadow")

        pig.acclimation_timer = self._ACCLIMATION_HOURS - 0.5
        pig.acclimating_biome = "alpine"
        update_acclimation(pig, "alpine", 1.0)

        assert pig.preferred_biome == "alpine"
