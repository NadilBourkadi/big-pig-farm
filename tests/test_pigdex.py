"""Tests for the Pigdex system."""

import pytest

from big_pig_farm.entities.pigdex import (
    Pigdex,
    phenotype_key,
    phenotype_key_from_parts,
    key_to_display_name,
    key_to_rarity,
    get_all_phenotype_keys,
    get_discovery_reward,
    get_milestone_reward,
    TOTAL_PHENOTYPES,
)
from big_pig_farm.entities.genetics import (
    BaseColor,
    Pattern,
    ColorIntensity,
    RoanType,
    Rarity,
    Phenotype,
)


class TestPhenotypeKeys:
    """Tests for phenotype key generation."""

    def test_key_format(self):
        """Key should be colon-separated values."""
        key = phenotype_key_from_parts(
            BaseColor.BLACK, Pattern.SOLID, ColorIntensity.FULL, RoanType.NONE
        )
        assert key == "black:solid:full:none"

    def test_key_from_phenotype(self):
        """Key from Phenotype object should match parts-based key."""
        phenotype = Phenotype(
            base_color=BaseColor.CHOCOLATE,
            pattern=Pattern.DUTCH,
            intensity=ColorIntensity.CHINCHILLA,
            roan=RoanType.ROAN,
            rarity=Rarity.LEGENDARY,
        )
        key = phenotype_key(phenotype)
        expected = phenotype_key_from_parts(
            BaseColor.CHOCOLATE, Pattern.DUTCH, ColorIntensity.CHINCHILLA, RoanType.ROAN
        )
        assert key == expected

    def test_all_keys_unique(self):
        """All 72 phenotype keys should be unique."""
        keys = get_all_phenotype_keys()
        assert len(keys) == TOTAL_PHENOTYPES
        assert len(set(keys)) == TOTAL_PHENOTYPES

    def test_total_phenotypes_is_144(self):
        """8 colors x 3 patterns x 3 intensities x 2 roan = 144."""
        assert TOTAL_PHENOTYPES == 144


class TestKeyConversion:
    """Tests for key-to-display conversions."""

    def test_key_to_display_name(self):
        """Key should convert back to a readable display name."""
        key = "black:solid:full:none"
        name = key_to_display_name(key)
        assert name == "Black"

    def test_key_to_rarity(self):
        """Key should produce correct rarity."""
        common_key = "black:solid:full:none"
        assert key_to_rarity(common_key) == Rarity.COMMON

        # Dalmatian black = 2 rare points = RARE
        rare_key = "black:dalmatian:full:none"
        rarity = key_to_rarity(rare_key)
        assert rarity == Rarity.RARE


class TestPigdex:
    """Tests for Pigdex model."""

    def test_empty_pigdex(self):
        """New pigdex should be empty."""
        pigdex = Pigdex()
        assert pigdex.discovered_count == 0
        assert pigdex.total_possible == 144
        assert pigdex.completion_percent == 0.0

    def test_register_new_phenotype(self):
        """Registering a new phenotype returns True."""
        pigdex = Pigdex()
        result = pigdex.register_phenotype("black:solid:full:none", 1)
        assert result is True
        assert pigdex.discovered_count == 1

    def test_register_duplicate_phenotype(self):
        """Registering an already-known phenotype returns False."""
        pigdex = Pigdex()
        pigdex.register_phenotype("black:solid:full:none", 1)
        result = pigdex.register_phenotype("black:solid:full:none", 2)
        assert result is False
        assert pigdex.discovered_count == 1

    def test_is_discovered(self):
        """is_discovered correctly reports status."""
        pigdex = Pigdex()
        key = "black:solid:full:none"
        assert not pigdex.is_discovered(key)
        pigdex.register_phenotype(key, 1)
        assert pigdex.is_discovered(key)

    def test_completion_percent(self):
        """Completion percentage should be accurate."""
        pigdex = Pigdex()
        # Register 36 of 144 = 25%
        keys = get_all_phenotype_keys()[:36]
        for key in keys:
            pigdex.register_phenotype(key, 1)
        assert pigdex.completion_percent == pytest.approx(25.0)

    def test_milestones(self):
        """Milestones should trigger at correct thresholds."""
        pigdex = Pigdex()
        keys = get_all_phenotype_keys()

        # Register 35 (just under 25%) - no milestone
        for key in keys[:35]:
            pigdex.register_phenotype(key, 1)
        assert pigdex.check_milestones() == []

        # Register 36th (exactly 25%) - milestone!
        pigdex.register_phenotype(keys[35], 1)
        milestones = pigdex.check_milestones()
        assert 25 in milestones

        # Claim it
        pigdex.claim_milestone(25)
        assert 25 in pigdex.milestone_rewards_claimed

        # Should not trigger again
        assert pigdex.check_milestones() == []


class TestRewards:
    """Tests for discovery and milestone rewards."""

    def test_discovery_rewards_scale_with_rarity(self):
        """Higher rarity should give more reward."""
        common = get_discovery_reward(Rarity.COMMON)
        uncommon = get_discovery_reward(Rarity.UNCOMMON)
        rare = get_discovery_reward(Rarity.RARE)
        legendary = get_discovery_reward(Rarity.LEGENDARY)

        assert common < uncommon < rare < legendary

    def test_milestone_rewards_scale(self):
        """Higher milestones should give more reward."""
        r25 = get_milestone_reward(25)
        r50 = get_milestone_reward(50)
        r75 = get_milestone_reward(75)
        r100 = get_milestone_reward(100)

        assert r25 < r50 < r75 < r100
        assert r100 == 10000
