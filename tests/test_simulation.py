"""Tests for the simulation systems."""

import pytest
from unittest.mock import patch
from big_pig_farm.data.config import NEEDS as NEEDS_CONFIG, BEHAVIOR, BREEDING
from big_pig_farm.entities.guinea_pig import GuineaPig, Gender, BehaviorState, Needs, Position
from big_pig_farm.simulation.behavior import BehaviorController
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


class TestStuckTimer:
    """Tests for the stuck-position timer in BehaviorController."""

    def test_stuck_pig_triggers_fallback_despite_alternatives(self):
        """Pig stuck at the same grid cell for >5s triggers give-up even when
        _try_alternative_facility succeeds (would normally reset _blocked_timers)."""
        state = GameState()
        controller = BehaviorController(state)

        # Create the stuck pig with a path and a waypoint it can't reach
        pig = GuineaPig.create(
            name="Stuck Pig",
            gender=Gender.MALE,
            position=Position(x=10.0, y=10.0),
            age_days=5.0,
        )
        pig.behavior_state = BehaviorState.WANDERING
        pig.path = [(12, 10)]  # Waypoint far enough to hit the mid-path branch
        pig.target_position = Position(x=12.0, y=10.0)
        pig.target_description = "going to Food Bowl"
        state.guinea_pigs[pig.id] = pig

        # Create a blocking pig directly in the path
        blocker = GuineaPig.create(
            name="Blocker",
            gender=Gender.FEMALE,
            position=Position(x=11.0, y=10.0),
            age_days=5.0,
        )
        blocker.behavior_state = BehaviorState.IDLE
        state.guinea_pigs[blocker.id] = blocker

        fallback_called = False
        original_fallback = controller._give_up_and_fallback

        def tracking_fallback(p):
            nonlocal fallback_called
            fallback_called = True
            original_fallback(p)

        # Patch _try_dodge to always fail (simulating a narrow corridor)
        # and _try_alternative_facility to always "succeed" (resets _blocked_timers)
        with patch.object(controller, '_try_dodge', return_value=False), \
             patch.object(controller.facility_manager, 'try_alternative_facility', return_value=True), \
             patch.object(controller, '_give_up_and_fallback', side_effect=tracking_fallback):

            # Simulate 6 seconds of being blocked at the same position (in 0.1s steps)
            for _ in range(60):
                if fallback_called:
                    break
                controller._update_movement(pig, 0.1)
                # _try_alternative_facility resets _blocked_timers but doesn't
                # actually move the pig, so re-give a path for next iteration
                if not pig.path:
                    pig.path = [(12, 10)]
                    pig.target_position = Position(x=12.0, y=10.0)

            # _give_up_and_fallback should have been called because the stuck
            # timer (tracking position, not blocked_timers) exceeded 5s
            assert fallback_called

    def test_stuck_timer_resets_on_movement(self):
        """Stuck timer resets when the pig actually moves to a new grid cell."""
        state = GameState()
        controller = BehaviorController(state)

        pig = GuineaPig.create(
            name="Moving Pig",
            gender=Gender.MALE,
            position=Position(x=10.0, y=10.0),
            age_days=5.0,
        )
        pig.behavior_state = BehaviorState.WANDERING
        pig.path = [(12, 10)]
        pig.target_position = Position(x=12.0, y=10.0)
        state.guinea_pigs[pig.id] = pig

        # Create a blocking pig directly in the path
        blocker = GuineaPig.create(
            name="Blocker",
            gender=Gender.FEMALE,
            position=Position(x=11.0, y=10.0),
            age_days=5.0,
        )
        blocker.behavior_state = BehaviorState.IDLE
        state.guinea_pigs[blocker.id] = blocker

        # Simulate being blocked for 4 seconds (just under threshold)
        with patch.object(controller, '_try_dodge', return_value=False), \
             patch.object(controller.facility_manager, 'try_alternative_facility', return_value=True):
            for _ in range(40):
                controller._update_movement(pig, 0.1)
                if not pig.path:
                    pig.path = [(12, 10)]
                    pig.target_position = Position(x=12.0, y=10.0)

        # Stuck timer should be ~4.0s
        assert controller._stuck_timers.get(pig.id, 0) > 3.5

        # Remove the blocker so the pig can move
        del state.guinea_pigs[blocker.id]

        # Give the pig a new path from its current position
        pig.path = [(11, 10), (12, 10)]
        pig.target_position = Position(x=12.0, y=10.0)

        # Simulate movement succeeding (no blocker now)
        controller._update_movement(pig, 0.1)

        # Stuck timer should be cleared since pig actually moved
        assert pig.id not in controller._stuck_timers


class TestLowPopHappinessBoost:
    """Tests for the low-population happiness boost."""

    def test_happiness_boost_when_population_low(self):
        """Happiness boost should apply when pig count <= MIN_BREEDING_POPULATION."""
        state = GameState()
        # Add only 2 pigs (below MIN_BREEDING_POPULATION)
        pig = GuineaPig.create(
            name="Lonely",
            gender=Gender.MALE,
            position=Position(x=5.0, y=5.0),
            age_days=5.0,
        )
        pig.needs.happiness = 50.0
        state.add_guinea_pig(pig)

        other = GuineaPig.create(
            name="Friend",
            gender=Gender.FEMALE,
            position=Position(x=20.0, y=20.0),
            age_days=5.0,
        )
        state.add_guinea_pig(other)

        assert len(state.get_pigs_list()) <= BREEDING.MIN_BREEDING_POPULATION

        update_all_needs(pig, 60.0, state)  # 1 game hour

        # With base decay of 2.0/hr + boredom penalty, but +5.0/hr boost,
        # happiness should be higher than (50 - 2.0 - 1.0) = 47.0
        # The boost gives +5.0 so net is roughly +2.0/hr depending on boredom
        assert pig.needs.happiness > 45.0

    def test_no_boost_when_population_above_threshold(self):
        """Happiness boost should NOT apply when pig count > MIN_BREEDING_POPULATION."""
        state = GameState()
        pig = GuineaPig.create(
            name="Test",
            gender=Gender.MALE,
            position=Position(x=5.0, y=5.0),
            age_days=5.0,
        )
        pig.needs.happiness = 50.0
        state.add_guinea_pig(pig)

        # Add enough other pigs to exceed MIN_BREEDING_POPULATION
        for i in range(BREEDING.MIN_BREEDING_POPULATION):
            other = GuineaPig.create(
                name=f"Other{i}",
                gender=Gender.FEMALE,
                position=Position(x=20.0, y=20.0),
                age_days=5.0,
            )
            state.add_guinea_pig(other)

        assert len(state.get_pigs_list()) > BREEDING.MIN_BREEDING_POPULATION

        update_all_needs(pig, 60.0, state)  # 1 game hour

        # Without boost, happiness should drop (base decay 2.0/hr + boredom)
        # Pig is far from others so no social boost to offset
        assert pig.needs.happiness < 50.0

    def test_boredom_recovery_when_population_low(self):
        """Boredom should decrease when pig count <= MIN_BREEDING_POPULATION."""
        state = GameState()
        pig = GuineaPig.create(
            name="Bored",
            gender=Gender.MALE,
            position=Position(x=5.0, y=5.0),
            age_days=5.0,
        )
        pig.needs.boredom = 80.0
        state.add_guinea_pig(pig)

        other = GuineaPig.create(
            name="Friend",
            gender=Gender.FEMALE,
            position=Position(x=20.0, y=20.0),
            age_days=5.0,
        )
        state.add_guinea_pig(other)

        assert len(state.get_pigs_list()) <= BREEDING.MIN_BREEDING_POPULATION

        update_all_needs(pig, 60.0, state)  # 1 game hour

        # Boredom gains +2.0/hr (decay) but loses -3.0/hr (low-pop recovery)
        # Net: -1.0/hr, so boredom should drop from 80
        assert pig.needs.boredom < 80.0

    def test_no_boredom_recovery_when_population_above_threshold(self):
        """Boredom should NOT get low-pop recovery when pig count > MIN_BREEDING_POPULATION."""
        state = GameState()
        pig = GuineaPig.create(
            name="Bored",
            gender=Gender.MALE,
            position=Position(x=5.0, y=5.0),
            age_days=5.0,
        )
        pig.needs.boredom = 50.0
        state.add_guinea_pig(pig)

        for i in range(BREEDING.MIN_BREEDING_POPULATION):
            other = GuineaPig.create(
                name=f"Other{i}",
                gender=Gender.FEMALE,
                position=Position(x=20.0, y=20.0),
                age_days=5.0,
            )
            state.add_guinea_pig(other)

        assert len(state.get_pigs_list()) > BREEDING.MIN_BREEDING_POPULATION

        update_all_needs(pig, 60.0, state)  # 1 game hour

        # Without low-pop recovery, boredom should increase (base +2.0/hr)
        assert pig.needs.boredom > 50.0
