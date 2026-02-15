"""Tests for biome data models."""

import pytest

from big_pig_farm.entities.biomes import BiomeType, BiomeInfo, BIOMES


class TestBiomeType:
    def test_all_biomes_defined(self):
        """Every BiomeType has an entry in BIOMES."""
        for biome_type in BiomeType:
            assert biome_type in BIOMES

    def test_biome_info_fields(self):
        """BiomeInfo has all required fields."""
        for biome_type, info in BIOMES.items():
            assert isinstance(info, BiomeInfo)
            assert info.display_name
            assert info.description
            assert info.required_tier >= 1
            assert info.cost >= 0
            assert info.floor_chars
            assert info.floor_colors
            assert info.floor_bg

    def test_meadow_is_free(self):
        """Meadow biome costs nothing and requires tier 1."""
        meadow = BIOMES[BiomeType.MEADOW]
        assert meadow.cost == 0
        assert meadow.required_tier == 1

    def test_sanctuary_is_highest_tier(self):
        """Sanctuary requires the highest tier."""
        sanctuary = BIOMES[BiomeType.SANCTUARY]
        assert sanctuary.required_tier == 5
        assert sanctuary.cost > 0
        assert len(sanctuary.mutation_boost_loci) == 5  # All loci boosted

    def test_mutation_boosts_are_positive(self):
        """All mutation boosts should be positive floats."""
        for biome_type, info in BIOMES.items():
            for locus, rate in info.mutation_boost_loci.items():
                assert rate > 0, f"{biome_type}: {locus} has non-positive rate"

    def test_tier_ordering(self):
        """Higher-tier biomes should cost more than lower-tier ones."""
        by_tier = sorted(BIOMES.values(), key=lambda i: i.required_tier)
        prev_max_cost = 0
        prev_tier = 0
        for info in by_tier:
            if info.required_tier > prev_tier:
                if prev_tier > 0:
                    assert info.cost >= prev_max_cost
                prev_tier = info.required_tier
                prev_max_cost = info.cost
            else:
                prev_max_cost = max(prev_max_cost, info.cost)
