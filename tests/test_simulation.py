"""Tests for the simulation systems."""

import pytest
from unittest.mock import patch
from big_pig_farm.data.config import NEEDS as NEEDS_CONFIG, BEHAVIOR
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


class TestContentmentModel:
    """Tests for the needs-derived contentment happiness model."""

    def test_happiness_recovers_when_needs_met(self):
        """Happiness should increase when all basic needs are above LOW_THRESHOLD."""
        state = GameState()
        pig = GuineaPig.create(
            name="Content",
            gender=Gender.MALE,
            position=Position(x=5.0, y=5.0),
            age_days=5.0,
        )
        pig.needs.happiness = 50.0
        pig.needs.hunger = 80.0
        pig.needs.thirst = 80.0
        pig.needs.energy = 80.0
        pig.needs.boredom = 0.0  # No boredom penalty
        state.add_guinea_pig(pig)

        update_all_needs(pig, 60.0, state)  # 1 game hour

        # Contentment recovery of +2.0/hr should increase happiness
        assert pig.needs.happiness > 50.0

    def test_happiness_drains_when_needs_critical(self):
        """Happiness should decrease when basic needs are below CRITICAL_THRESHOLD."""
        state = GameState()
        pig = GuineaPig.create(
            name="Suffering",
            gender=Gender.MALE,
            position=Position(x=5.0, y=5.0),
            age_days=5.0,
        )
        pig.needs.happiness = 50.0
        pig.needs.hunger = 5.0   # Critical
        pig.needs.thirst = 5.0   # Critical
        pig.needs.energy = 5.0   # Critical
        state.add_guinea_pig(pig)

        update_all_needs(pig, 60.0, state)  # 1 game hour

        # All three critical: -2.0 - 2.5 - 1.5 = -6.0/hr drain
        assert pig.needs.happiness < 50.0

    def test_no_happiness_change_when_needs_moderate(self):
        """Happiness should stay roughly stable when needs are between critical and low."""
        state = GameState()
        pig = GuineaPig.create(
            name="Moderate",
            gender=Gender.MALE,
            position=Position(x=5.0, y=5.0),
            age_days=5.0,
        )
        pig.needs.happiness = 50.0
        pig.needs.hunger = 30.0   # Above critical, below low threshold
        pig.needs.thirst = 30.0
        pig.needs.energy = 30.0
        pig.needs.boredom = 0.0
        state.add_guinea_pig(pig)

        update_all_needs(pig, 60.0, state)  # 1 game hour

        # Not critical (no drain) and not satisfied (no recovery) — should stay ~50
        # Only boredom extra drain could change it, but boredom starts at 0
        # After 1hr boredom rises to ~2.0 which is below the 70 threshold
        assert 48.0 < pig.needs.happiness < 52.0


class TestWanderDensityScoring:
    """Tests for density-aware wander target selection."""

    def test_wander_prefers_less_crowded_area(self):
        """Pig should prefer wandering to positions with fewer nearby pigs."""
        from big_pig_farm.game.world import FarmGrid
        from big_pig_farm.data.config import FARM_TIERS

        tier_info = FARM_TIERS[2]  # Tier 3 — large enough for meaningful spread
        farm = FarmGrid(width=tier_info.width, height=tier_info.height, tier=3)
        state = GameState(farm=farm)
        controller = BehaviorController(state)

        # Create a cluster of pigs in one corner
        for i in range(5):
            cluster_pig = GuineaPig.create(
                name=f"ClusterPig{i}",
                gender=Gender.MALE,
                position=Position(x=5.0 + i, y=5.0),
                age_days=5.0,
            )
            cluster_pig.behavior_state = BehaviorState.IDLE
            state.guinea_pigs[cluster_pig.id] = cluster_pig

        # Create the test pig near the cluster
        test_pig = GuineaPig.create(
            name="TestPig",
            gender=Gender.MALE,
            position=Position(x=8.0, y=5.0),
            age_days=5.0,
        )
        state.guinea_pigs[test_pig.id] = test_pig

        # Run wandering multiple times and check that pig tends to move away
        moved_away_count = 0
        trials = 20
        initial_cluster_dist = test_pig.position.distance_to(
            Position(x=7.0, y=5.0)  # Approximate cluster center
        )

        for _ in range(trials):
            test_pig.position.x = 8.0
            test_pig.position.y = 5.0
            test_pig.path = []
            controller._start_wandering(test_pig)
            if test_pig.target_position:
                new_dist = test_pig.target_position.distance_to(
                    Position(x=7.0, y=5.0)
                )
                if new_dist > initial_cluster_dist:
                    moved_away_count += 1

        # Should move away from the cluster more often than toward it
        assert moved_away_count > trials * 0.4

    def test_wander_works_with_no_other_pigs(self):
        """Wandering should work fine when pig is alone."""
        from big_pig_farm.game.world import FarmGrid
        from big_pig_farm.data.config import FARM_TIERS

        tier_info = FARM_TIERS[2]
        farm = FarmGrid(width=tier_info.width, height=tier_info.height, tier=3)
        state = GameState(farm=farm)
        controller = BehaviorController(state)

        pig = GuineaPig.create(
            name="LonePig",
            gender=Gender.MALE,
            position=Position(x=10.0, y=10.0),
            age_days=5.0,
        )
        state.guinea_pigs[pig.id] = pig

        controller._start_wandering(pig)
        assert pig.behavior_state == BehaviorState.WANDERING


class TestIdleDrift:
    """Tests for idle drift anti-clustering."""

    def test_idle_becomes_wander_when_pig_nearby(self):
        """When another pig is within IDLE_DRIFT_RADIUS, idle converts to wander."""
        from big_pig_farm.game.world import FarmGrid
        from big_pig_farm.data.config import FARM_TIERS

        tier_info = FARM_TIERS[2]
        farm = FarmGrid(width=tier_info.width, height=tier_info.height, tier=3)
        state = GameState(farm=farm)
        controller = BehaviorController(state)

        pig = GuineaPig.create(
            name="IdlePig",
            gender=Gender.MALE,
            position=Position(x=10.0, y=10.0),
            age_days=5.0,
        )
        pig.needs.hunger = 90
        pig.needs.thirst = 90
        pig.needs.energy = 90
        pig.needs.happiness = 90
        pig.needs.social = 90
        pig.needs.boredom = 0
        state.guinea_pigs[pig.id] = pig

        neighbor = GuineaPig.create(
            name="Neighbor",
            gender=Gender.FEMALE,
            position=Position(x=12.0, y=10.0),  # Within IDLE_DRIFT_RADIUS (5.0)
            age_days=5.0,
        )
        neighbor.needs.hunger = 90
        neighbor.needs.thirst = 90
        neighbor.needs.energy = 90
        neighbor.needs.happiness = 90
        neighbor.needs.social = 90
        state.guinea_pigs[neighbor.id] = neighbor

        # Force the pig to make a decision where it would normally idle
        # by patching random to return > WANDER_CHANCE
        with patch('big_pig_farm.simulation.behavior.random') as mock_random:
            mock_random.random.return_value = 0.99  # > WANDER_CHANCE (0.8), would normally idle
            mock_random.uniform.return_value = 0.0
            controller._make_decision(pig)

        # Should be wandering (drifted away) instead of idle
        assert pig.behavior_state == BehaviorState.WANDERING

    def test_idle_stays_idle_when_no_pig_nearby(self):
        """When no pig is within IDLE_DRIFT_RADIUS, pig stays idle."""
        from big_pig_farm.game.world import FarmGrid
        from big_pig_farm.data.config import FARM_TIERS

        tier_info = FARM_TIERS[2]
        farm = FarmGrid(width=tier_info.width, height=tier_info.height, tier=3)
        state = GameState(farm=farm)
        controller = BehaviorController(state)

        pig = GuineaPig.create(
            name="IdlePig",
            gender=Gender.MALE,
            position=Position(x=10.0, y=10.0),
            age_days=5.0,
        )
        pig.needs.hunger = 90
        pig.needs.thirst = 90
        pig.needs.energy = 90
        pig.needs.happiness = 90
        pig.needs.social = 90
        pig.needs.boredom = 0
        state.guinea_pigs[pig.id] = pig

        far_pig = GuineaPig.create(
            name="FarPig",
            gender=Gender.FEMALE,
            position=Position(x=50.0, y=50.0),  # Well outside IDLE_DRIFT_RADIUS
            age_days=5.0,
        )
        far_pig.needs.hunger = 90
        far_pig.needs.thirst = 90
        far_pig.needs.energy = 90
        far_pig.needs.happiness = 90
        far_pig.needs.social = 90
        state.guinea_pigs[far_pig.id] = far_pig

        with patch('big_pig_farm.simulation.behavior.random') as mock_random:
            mock_random.random.return_value = 0.99
            mock_random.uniform.return_value = 0.0
            controller._make_decision(pig)

        assert pig.behavior_state == BehaviorState.IDLE
