"""Tests for the bloodline system."""

import pytest

from big_pig_farm.entities.bloodlines import (
    BloodlineType,
    Bloodline,
    BLOODLINES,
    get_available_bloodlines,
    generate_bloodline_pig_genotype,
    pick_random_bloodline,
)
from big_pig_farm.entities.genetics import Genotype


class TestBloodlineDefinitions:
    """Tests for bloodline definitions."""

    def test_all_bloodlines_defined(self):
        """All BloodlineType values have a corresponding entry in BLOODLINES."""
        for bt in BloodlineType:
            assert bt in BLOODLINES, f"Missing bloodline definition for {bt}"

    def test_bloodline_has_required_fields(self):
        """Each bloodline has all required fields."""
        for bt, bloodline in BLOODLINES.items():
            assert bloodline.display_name
            assert bloodline.description
            assert bloodline.required_tier >= 1
            assert bloodline.cost_multiplier >= 1.0
            assert bloodline.locus_overrides

    def test_tier_ordering(self):
        """Lower tiers have cheaper bloodlines."""
        tier1 = [b for b in BLOODLINES.values() if b.required_tier == 1]
        tier4 = [b for b in BLOODLINES.values() if b.required_tier == 4]
        assert tier1 and tier4
        max_tier1_cost = max(b.cost_multiplier for b in tier1)
        min_tier4_cost = min(b.cost_multiplier for b in tier4)
        assert max_tier1_cost < min_tier4_cost


class TestBloodlineAvailability:
    """Tests for bloodline tier gating."""

    def test_tier1_has_bloodlines(self):
        """Tier 1 should have at least Spotted and Chocolate."""
        available = get_available_bloodlines(1)
        types = {b.bloodline_type for b in available}
        assert BloodlineType.SPOTTED in types
        assert BloodlineType.CHOCOLATE in types

    def test_tier2_adds_more(self):
        """Tier 2 should include tier 1 plus Golden and Silver."""
        available = get_available_bloodlines(2)
        types = {b.bloodline_type for b in available}
        assert BloodlineType.GOLDEN in types
        assert BloodlineType.SILVER in types
        assert BloodlineType.SPOTTED in types  # Tier 1 still available

    def test_tier3_adds_roan(self):
        """Tier 3 should include Roan."""
        available = get_available_bloodlines(3)
        types = {b.bloodline_type for b in available}
        assert BloodlineType.ROAN in types

    def test_tier4_has_all(self):
        """Tier 4+ should have all bloodlines."""
        available = get_available_bloodlines(4)
        assert len(available) == len(BLOODLINES)


class TestBloodlineGenotype:
    """Tests for bloodline genotype generation."""

    def test_spotted_carrier(self):
        """Spotted bloodline should produce S/s genotype."""
        bloodline = BLOODLINES[BloodlineType.SPOTTED]
        genotype = generate_bloodline_pig_genotype(bloodline)
        assert genotype.s_locus == ("S", "s")

    def test_chocolate_carrier(self):
        """Chocolate bloodline should produce B/b genotype."""
        bloodline = BLOODLINES[BloodlineType.CHOCOLATE]
        genotype = generate_bloodline_pig_genotype(bloodline)
        assert genotype.b_locus == ("B", "b")

    def test_roan_carrier(self):
        """Roan bloodline should produce R/r genotype."""
        bloodline = BLOODLINES[BloodlineType.ROAN]
        genotype = generate_bloodline_pig_genotype(bloodline)
        assert genotype.r_locus == ("R", "r")

    def test_exotic_spot_silver_carrier(self):
        """Exotic Spot+Silver should have both S/s and C/ch."""
        bloodline = BLOODLINES[BloodlineType.EXOTIC_SPOT_SILVER]
        genotype = generate_bloodline_pig_genotype(bloodline)
        assert genotype.s_locus == ("S", "s")
        assert genotype.c_locus == ("C", "ch")

    def test_apply_preserves_other_loci(self):
        """Applying a bloodline should only change specified loci."""
        bloodline = BLOODLINES[BloodlineType.SPOTTED]
        genotype = generate_bloodline_pig_genotype(bloodline)
        # s_locus is overridden
        assert genotype.s_locus == ("S", "s")
        # Other loci should still be common
        assert genotype.c_locus == ("C", "C")
        assert genotype.r_locus == ("r", "r")

    def test_pick_random_bloodline_returns_none_for_tier_0(self):
        """Tier 0 should have no bloodlines (none require tier 0)."""
        # All bloodlines require tier >= 1, so tier 0 should return None
        result = pick_random_bloodline(0)
        assert result is None
