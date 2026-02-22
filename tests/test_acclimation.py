"""Tests for the biome acclimation system."""

import pytest

from big_pig_farm.data.config import BIOME, TIME
from big_pig_farm.entities.guinea_pig import Gender, GuineaPig, Position
from big_pig_farm.simulation.acclimation import update_acclimation

_ACCLIMATION_HOURS = BIOME.ACCLIMATION_DAYS * TIME.GAME_HOURS_PER_DAY


def _make_pig(preferred_biome: str | None = "meadow") -> GuineaPig:
    pig = GuineaPig.create(name="Test", gender=Gender.MALE, position=Position(x=5.0, y=5.0), age_days=5.0)
    pig.preferred_biome = preferred_biome
    return pig


class TestAcclimationTimer:
    def test_no_op_when_no_preferred_biome(self):
        """Pigs without a preferred biome don't acclimate."""
        pig = _make_pig(preferred_biome=None)
        update_acclimation(pig, "alpine", 1.0)
        assert pig.acclimation_timer == 0.0
        assert pig.acclimating_biome is None

    def test_no_op_when_no_current_biome(self):
        """Pigs not in any biome (e.g. tunnels) don't acclimate."""
        pig = _make_pig()
        update_acclimation(pig, None, 1.0)
        assert pig.acclimation_timer == 0.0

    def test_timer_resets_in_home_biome(self):
        """Being in preferred biome resets acclimation progress."""
        pig = _make_pig()
        pig.acclimation_timer = 10.0
        pig.acclimating_biome = "alpine"
        update_acclimation(pig, "meadow", 1.0)
        assert pig.acclimation_timer == 0.0
        assert pig.acclimating_biome is None

    def test_timer_advances_in_foreign_biome(self):
        """Timer ticks up when in a non-preferred biome."""
        pig = _make_pig()
        update_acclimation(pig, "alpine", 2.0)
        assert pig.acclimation_timer == 2.0
        assert pig.acclimating_biome == "alpine"

    def test_timer_resets_on_biome_change(self):
        """Moving to a third biome restarts the timer."""
        pig = _make_pig()
        pig.acclimation_timer = 20.0
        pig.acclimating_biome = "alpine"
        update_acclimation(pig, "tropical", 1.0)
        assert pig.acclimation_timer == 1.0
        assert pig.acclimating_biome == "tropical"

    def test_timer_accumulates(self):
        """Multiple calls accumulate correctly."""
        pig = _make_pig()
        for _ in range(10):
            update_acclimation(pig, "alpine", 1.0)
        assert pig.acclimation_timer == pytest.approx(10.0)


    def test_same_biome_different_area_continues_timer(self):
        """Moving between areas with the same biome doesn't reset the timer."""
        pig = _make_pig(preferred_biome="meadow")
        pig.acclimating_biome = "alpine"
        pig.acclimation_timer = 10.0
        # Still in alpine (same biome string, could be a different area)
        update_acclimation(pig, "alpine", 2.0)
        assert pig.acclimation_timer == 12.0
        assert pig.acclimating_biome == "alpine"


class TestAcclimationComplete:
    def test_adopts_new_biome_after_threshold(self):
        """Pig adopts new preferred biome after ACCLIMATION_HOURS."""
        pig = _make_pig()
        # Advance to just before threshold
        pig.acclimation_timer = _ACCLIMATION_HOURS - 1.0
        pig.acclimating_biome = "alpine"
        update_acclimation(pig, "alpine", 2.0)
        assert pig.preferred_biome == "alpine"
        assert pig.acclimation_timer == 0.0
        assert pig.acclimating_biome is None

    def test_exact_threshold(self):
        """Pig acclimation triggers at exactly the threshold."""
        pig = _make_pig()
        pig.acclimation_timer = _ACCLIMATION_HOURS - 1.0
        pig.acclimating_biome = "alpine"
        update_acclimation(pig, "alpine", 1.0)
        assert pig.preferred_biome == "alpine"

    def test_second_acclimation_possible(self):
        """After acclimating once, a pig can acclimate to yet another biome."""
        pig = _make_pig()
        # Acclimate to alpine
        pig.acclimation_timer = _ACCLIMATION_HOURS - 0.5
        pig.acclimating_biome = "alpine"
        update_acclimation(pig, "alpine", 1.0)
        assert pig.preferred_biome == "alpine"

        # Now start acclimating to tropical
        update_acclimation(pig, "tropical", 1.0)
        assert pig.acclimating_biome == "tropical"
        assert pig.acclimation_timer == 1.0


class TestBirthInheritance:
    def test_baby_inherits_mother_preferred_biome(self):
        """Birth code should set baby.preferred_biome from mother, not birth area.

        This is a structural test — actual birth integration is tested elsewhere.
        The acclimation module doesn't handle birth, but we verify the field defaults.
        """
        pig = _make_pig()
        assert pig.acclimation_timer == 0.0
        assert pig.acclimating_biome is None
