"""Tests for biome selection constraints (uniqueness + tier ordering)."""

from big_pig_farm.entities.biomes import BiomeType
from big_pig_farm.ui.screens.biome_select import _missing_tier


class TestMissingTier:
    """Tests for _missing_tier helper."""

    def test_no_missing_tier_for_tier_1_biome(self):
        assert _missing_tier(BiomeType.MEADOW, set()) is None
        assert _missing_tier(BiomeType.BURROW, set()) is None

    def test_tier_2_needs_tier_1(self):
        assert _missing_tier(BiomeType.GARDEN, set()) == 1
        assert _missing_tier(BiomeType.GARDEN, {1}) is None

    def test_tier_3_needs_tier_1_and_2(self):
        assert _missing_tier(BiomeType.ALPINE, set()) == 1
        assert _missing_tier(BiomeType.ALPINE, {1}) == 2
        assert _missing_tier(BiomeType.ALPINE, {1, 2}) is None

    def test_tier_5_needs_all_lower(self):
        assert _missing_tier(BiomeType.SANCTUARY, set()) == 1
        assert _missing_tier(BiomeType.SANCTUARY, {1, 2, 3}) == 4
        assert _missing_tier(BiomeType.SANCTUARY, {1, 2, 3, 4}) is None

    def test_returns_lowest_missing(self):
        assert _missing_tier(BiomeType.SANCTUARY, {2, 4}) == 1
        assert _missing_tier(BiomeType.SANCTUARY, {1, 4}) == 2


class TestBiomeStatus:
    """Tests for BiomeSelectScreen._biome_status via direct instantiation."""

    def _make_screen(self, farm_tier: int, existing_biomes: set[BiomeType]):
        from big_pig_farm.ui.screens.biome_select import BiomeSelectScreen
        return BiomeSelectScreen(farm_tier=farm_tier, existing_biomes=existing_biomes)

    def _status(self, farm_tier, existing_biomes, biome):
        from big_pig_farm.entities.biomes import BIOMES
        screen = self._make_screen(farm_tier, existing_biomes)
        return screen._biome_status(biome, BIOMES[biome])

    def test_already_built_biome_unavailable(self):
        available, reason = self._status(5, {BiomeType.MEADOW}, BiomeType.MEADOW)
        assert not available
        assert reason == "built"

    def test_tier_too_high_shows_tier_lock(self):
        available, reason = self._status(1, {BiomeType.MEADOW}, BiomeType.GARDEN)
        assert not available
        assert reason == "tier 2"

    def test_missing_prerequisite_tier(self):
        # Farm tier is 3, but no tier 2 biome built yet
        available, reason = self._status(3, {BiomeType.MEADOW}, BiomeType.ALPINE)
        assert not available
        assert reason == "build a tier 2 biome first"

    def test_available_when_all_conditions_met(self):
        existing = {BiomeType.MEADOW, BiomeType.GARDEN}
        available, reason = self._status(3, existing, BiomeType.ALPINE)
        assert available
        assert reason is None

    def test_built_takes_priority_over_other_locks(self):
        # Even if tier is too high, "built" should be the reason
        available, reason = self._status(1, {BiomeType.SANCTUARY}, BiomeType.SANCTUARY)
        assert not available
        assert reason == "built"

    def test_tier_lock_before_prerequisite_check(self):
        # Tier 5 biome at farm tier 2 — tier lock should show, not prerequisite
        available, reason = self._status(2, {BiomeType.MEADOW}, BiomeType.SANCTUARY)
        assert not available
        assert reason == "tier 5"

    def test_starter_biome_always_built(self):
        # Meadow is always present (starter)
        available, reason = self._status(1, {BiomeType.MEADOW}, BiomeType.MEADOW)
        assert not available
        assert reason == "built"
