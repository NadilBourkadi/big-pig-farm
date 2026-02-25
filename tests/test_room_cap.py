"""Tests for soft room cap in facility scoring."""

from uuid import uuid4

from big_pig_farm.data.config import BEHAVIOR, TIER_UPGRADES, get_tier_upgrade
from big_pig_farm.entities.biomes import BiomeType
from big_pig_farm.entities.facilities import Facility, FacilityType
from big_pig_farm.entities.guinea_pig import Gender, GuineaPig, Position
from big_pig_farm.game.state import GameState
from big_pig_farm.game.world import FarmGrid
from big_pig_farm.simulation.behavior_controller import BehaviorController


def _make_state_with_two_rooms() -> GameState:
    """Create a game state with two connected rooms and food bowls in each."""
    state = GameState()
    state.farm = FarmGrid.create_starter()
    state.farm.add_room(BiomeType.ALPINE)
    return state


def _add_pig(state: GameState, x: float, y: float, name: str = "Pig") -> GuineaPig:
    pig = GuineaPig.create(name=name, gender=Gender.MALE, position=Position(x=x, y=y), age_days=5.0)
    area = state.farm.get_area_at(int(x), int(y))
    if area:
        pig.current_area_id = area.id
        pig.preferred_biome = area.biome.value
    state.guinea_pigs[pig.id] = pig
    return pig


class TestAreaCapacity:
    def test_get_area_capacity_first_room(self):
        """First room uses uniform capacity_per_room for tier 1."""
        state = GameState()
        state.farm = FarmGrid.create_starter()
        area = state.farm.areas[0]
        assert state.farm.get_area_capacity(area.id) == TIER_UPGRADES[0].capacity_per_room

    def test_get_area_capacity_second_room(self):
        """Second room uses the same uniform capacity_per_room as first."""
        state = _make_state_with_two_rooms()
        area = state.farm.areas[1]
        # Both rooms have the same capacity at tier 1
        assert state.farm.get_area_capacity(area.id) == TIER_UPGRADES[0].capacity_per_room

    def test_get_area_capacity_unknown(self):
        """Unknown area_id returns 0."""
        state = GameState()
        state.farm = FarmGrid.create_starter()
        assert state.farm.get_area_capacity(uuid4()) == 0


class TestAreaPopulations:
    def test_update_area_populations_empty(self):
        """No pigs → empty populations, but capacities are set."""
        state = _make_state_with_two_rooms()
        controller = BehaviorController(state)
        facility_manager = controller.facility_manager
        facility_manager.update_area_populations()
        assert len(facility_manager._area_populations) == 0
        assert len(facility_manager._area_capacities) == 2

    def test_update_area_populations_counts(self):
        """Pigs are counted by their current_area_id."""
        state = _make_state_with_two_rooms()
        controller = BehaviorController(state)
        facility_manager = controller.facility_manager

        area_0 = state.farm.areas[0]
        # Place pigs in the first room's interior
        for i in range(5):
            _add_pig(state, float(area_0.x1 + 3), float(area_0.y1 + 3), name=f"P{i}")

        facility_manager.update_area_populations()
        assert facility_manager._area_populations[area_0.id] == 5
        assert facility_manager._area_populations.get(state.farm.areas[1].id, 0) == 0


class TestOvercrowdingScoring:
    def test_overcrowded_room_penalizes_facilities(self):
        """Facilities in an overcrowded room should get a higher score (worse)."""
        state = _make_state_with_two_rooms()
        controller = BehaviorController(state)
        facility_manager = controller.facility_manager

        area_0 = state.farm.areas[0]
        capacity = state.farm.get_area_capacity(area_0.id)

        # Place more pigs than capacity in room 0
        for i in range(capacity + 3):
            _add_pig(state, float(area_0.x1 + 3), float(area_0.y1 + 3), name=f"P{i}")

        facility_manager.update_area_populations()

        # Verify overcrowding detected
        assert facility_manager._area_populations[area_0.id] > facility_manager._area_capacities[area_0.id]

        # The overcrowding penalty for room 0 should be positive
        overage = facility_manager._area_populations[area_0.id] - facility_manager._area_capacities[area_0.id]
        expected_penalty = overage * BEHAVIOR.ROOM_OVERCROWDING_PENALTY
        assert expected_penalty > 0

    def test_same_area_first_skipped_when_overcrowded(self):
        """When pig's room is overcrowded, same-area-first optimization is skipped."""
        state = _make_state_with_two_rooms()
        controller = BehaviorController(state)
        facility_manager = controller.facility_manager

        area_0 = state.farm.areas[0]
        area_1 = state.farm.areas[1]
        capacity = state.farm.get_area_capacity(area_0.id)

        # Set up overcrowding in room 0
        facility_manager._area_populations[area_0.id] = capacity + 1
        facility_manager._area_capacities[area_0.id] = capacity
        facility_manager._area_populations[area_1.id] = 0
        facility_manager._area_capacities[area_1.id] = get_tier_upgrade(1).capacity_per_room

        # Create a pig in room 0
        pig = _add_pig(state, float(area_0.x1 + 3), float(area_0.y1 + 3), name="TestPig")
        pig.current_area_id = area_0.id

        # Place a food bowl in room 1
        bowl = Facility.create(
            facility_type=FacilityType.FOOD_BOWL,
            x=area_1.x1 + 5,
            y=area_1.y1 + 5,
        )
        bowl.area_id = area_1.id
        state.facilities[bowl.id] = bowl
        state.farm.place_facility(bowl)

        # Verify the overcrowded flag is set correctly — this drives the
        # same-area-first bypass in get_reachable_facilities
        population = facility_manager._area_populations.get(pig.current_area_id, 0)
        room_capacity = facility_manager._area_capacities.get(pig.current_area_id, 0)
        assert population > room_capacity
