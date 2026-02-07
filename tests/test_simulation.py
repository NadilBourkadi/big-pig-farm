"""Tests for the simulation systems."""

import pytest
from big_pig_farm.data.config import NEEDS as NEEDS_CONFIG
from big_pig_farm.entities.guinea_pig import GuineaPig, Gender, Needs, Position
from big_pig_farm.simulation.needs import (
    update_all_needs,
    get_most_urgent_need,
    calculate_overall_wellbeing,
)
from big_pig_farm.game.state import GameState


class TestNeeds:
    """Tests for the needs system."""

    def test_needs_decay(self):
        """Test that needs decay over time."""
        pig = GuineaPig.create(
            name="Test Pig",
            gender=Gender.MALE,
            position=Position(x=5.0, y=5.0),
            age_days=5.0,
        )

        initial_hunger = pig.needs.hunger
        initial_thirst = pig.needs.thirst

        state = GameState()
        update_all_needs(pig, 60.0, state)  # 1 game hour

        assert pig.needs.hunger < initial_hunger
        assert pig.needs.thirst < initial_thirst

    def test_needs_clamping(self):
        """Test that needs stay within bounds."""
        pig = GuineaPig.create(
            name="Test Pig",
            gender=Gender.FEMALE,
            position=Position(x=5.0, y=5.0),
        )

        # Set extreme values
        pig.needs.hunger = -50
        pig.needs.happiness = 150

        pig.needs.clamp_all()

        assert pig.needs.hunger >= 0
        assert pig.needs.happiness <= 100

    def test_get_most_urgent_need(self):
        """Test identifying the most urgent need."""
        pig = GuineaPig.create(
            name="Test Pig",
            gender=Gender.MALE,
        )

        # All needs satisfied
        pig.needs.hunger = 90
        pig.needs.thirst = 90
        pig.needs.energy = 90
        pig.needs.happiness = 90
        pig.needs.social = 90

        urgent = get_most_urgent_need(pig)
        assert urgent == "none"

        # Make thirst critical
        pig.needs.thirst = 10
        urgent = get_most_urgent_need(pig)
        assert urgent == "thirst"

        # Thirst has priority over hunger (decays faster)
        # So even if hunger is lower, thirst is checked first
        pig.needs.hunger = 5
        urgent = get_most_urgent_need(pig)
        assert urgent == "thirst"  # Thirst still has priority

        # If thirst is satisfied, hunger becomes urgent
        pig.needs.thirst = 90
        urgent = get_most_urgent_need(pig)
        assert urgent == "hunger"

    def test_health_passive_recovery(self):
        """Test that health recovers passively when no needs are critical."""
        pig = GuineaPig.create(
            name="Test Pig",
            gender=Gender.MALE,
            position=Position(x=5.0, y=5.0),
            age_days=5.0,
        )
        pig.needs.hunger = 80
        pig.needs.thirst = 80
        pig.needs.health = 50

        state = GameState()
        update_all_needs(pig, 60.0, state)  # 1 game hour

        # Health should increase (passive recovery = 1.0/hr)
        assert pig.needs.health > 50

    def test_health_drain_reduced(self):
        """Test that health drain is reduced with new config values."""
        pig = GuineaPig.create(
            name="Test Pig",
            gender=Gender.MALE,
            position=Position(x=5.0, y=5.0),
            age_days=5.0,
        )
        pig.needs.hunger = 5  # Critical
        pig.needs.thirst = 5  # Critical
        pig.needs.health = 100

        state = GameState()
        update_all_needs(pig, 60.0, state)  # 1 game hour

        # Total drain should be ~0.8/hr (0.3 hunger + 0.5 thirst), not 1.5
        expected_drain = NEEDS_CONFIG.HEALTH_DRAIN_HUNGER + NEEDS_CONFIG.HEALTH_DRAIN_THIRST
        assert pig.needs.health >= 100 - expected_drain - 0.1
        assert pig.needs.health < 100

    def test_sleep_health_recovery_outpaces_drain(self):
        """Test that sleeping pig gains net health even with critical needs."""
        from big_pig_farm.entities.guinea_pig import BehaviorState

        pig = GuineaPig.create(
            name="Test Pig",
            gender=Gender.MALE,
            position=Position(x=5.0, y=5.0),
            age_days=5.0,
        )
        pig.needs.hunger = 5  # Critical
        pig.needs.thirst = 5  # Critical
        pig.needs.health = 50
        pig.behavior_state = BehaviorState.SLEEPING

        state = GameState()
        update_all_needs(pig, 60.0, state)  # 1 game hour

        # Net health change = +1.5 (sleep recovery) - 0.3 (hunger) - 0.5 (thirst) = +0.7
        assert pig.needs.health > 50

    def test_calculate_wellbeing(self):
        """Test overall wellbeing calculation."""
        pig = GuineaPig.create(
            name="Test Pig",
            gender=Gender.FEMALE,
        )

        # All needs at 100
        pig.needs.hunger = 100
        pig.needs.thirst = 100
        pig.needs.energy = 100
        pig.needs.happiness = 100
        pig.needs.health = 100

        wellbeing = calculate_overall_wellbeing(pig)
        assert wellbeing == 100.0

        # All needs at 50
        pig.needs.hunger = 50
        pig.needs.thirst = 50
        pig.needs.energy = 50
        pig.needs.happiness = 50
        pig.needs.health = 50

        wellbeing = calculate_overall_wellbeing(pig)
        assert wellbeing == 50.0


class TestGuineaPig:
    """Tests for guinea pig entity."""

    def test_create_guinea_pig(self):
        """Test creating a guinea pig."""
        pig = GuineaPig.create(
            name="Squeaky",
            gender=Gender.MALE,
            position=Position(x=5.0, y=5.0),
        )

        assert pig.name == "Squeaky"
        assert pig.gender == Gender.MALE
        assert pig.genotype is not None
        assert pig.phenotype is not None
        assert len(pig.personality) >= 1

    def test_age_groups(self):
        """Test age group determination."""
        pig = GuineaPig.create(
            name="Baby",
            gender=Gender.FEMALE,
            age_days=0.0,
        )
        assert pig.is_baby is True
        assert pig.is_adult is False

        pig.age_days = 5.0
        assert pig.is_baby is False
        assert pig.is_adult is True

        pig.age_days = 35.0
        assert pig.is_adult is False
        assert pig.is_senior is True

    def test_pig_value(self):
        """Test guinea pig valuation."""
        pig = GuineaPig.create(
            name="Test",
            gender=Gender.MALE,
            age_days=5.0,
        )

        value = pig.get_value()
        assert value > 0
        assert isinstance(value, int)

    def test_position_distance(self):
        """Test position distance calculation."""
        pos1 = Position(x=0.0, y=0.0)
        pos2 = Position(x=3.0, y=4.0)

        distance = pos1.distance_to(pos2)
        assert distance == 5.0  # 3-4-5 triangle
