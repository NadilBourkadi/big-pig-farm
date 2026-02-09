"""Tests for auto-arrange facility layout."""

import pytest

from big_pig_farm.data.config import FARM_TIERS
from big_pig_farm.entities.facilities import Facility, FacilityType, FACILITY_INFO
from big_pig_farm.entities.genetics import Genotype, calculate_phenotype
from big_pig_farm.entities.guinea_pig import GuineaPig, BehaviorState, Position, Gender
from big_pig_farm.game.auto_arrange import (
    calculate_zones,
    compute_arrangement,
    apply_arrangement,
    clear_pig_navigation,
    ZONE_FEEDING,
    ZONE_HYDRATION,
    ZONE_REST,
    ZONE_PLAY,
    ZONE_UTILITY,
)
from big_pig_farm.game.state import GameState
from big_pig_farm.game.world import FarmGrid


def _make_state(tier: int = 1) -> GameState:
    """Create a GameState with the specified farm tier."""
    tier_info = FARM_TIERS[tier - 1]
    farm = FarmGrid(width=tier_info.width, height=tier_info.height, tier=tier)
    return GameState(farm=farm)


def _add_facility(state: GameState, ftype: FacilityType, x: int = 5, y: int = 3) -> Facility:
    """Add a facility to the state at a valid position."""
    facility = Facility.create(ftype, x, y)
    state.add_facility(facility)
    return facility


def _make_pig(x: float = 5.0, y: float = 5.0) -> GuineaPig:
    """Create a pig at a given position."""
    genotype = Genotype.random()
    phenotype = calculate_phenotype(genotype)
    return GuineaPig(
        name="TestPig",
        genotype=genotype,
        phenotype=phenotype,
        gender=Gender.MALE,
        position=Position(x=x, y=y),
    )


class TestZoneCalculation:
    """Tests for zone boundary computation."""

    def test_tier1_produces_3_zones(self):
        """Tier 1 (30x15) is small — should produce 3 zones."""
        state = _make_state(tier=1)
        zones = calculate_zones(state.farm)
        assert len(zones) == 3
        zone_names = {z.name for z in zones}
        assert ZONE_FEEDING in zone_names
        assert ZONE_REST in zone_names
        assert ZONE_UTILITY in zone_names

    def test_tier3_produces_5_zones(self):
        """Tier 3 (50x25) is big — should produce 5 zones."""
        state = _make_state(tier=3)
        zones = calculate_zones(state.farm)
        assert len(zones) == 5
        zone_names = {z.name for z in zones}
        assert ZONE_FEEDING in zone_names
        assert ZONE_HYDRATION in zone_names
        assert ZONE_REST in zone_names
        assert ZONE_PLAY in zone_names
        assert ZONE_UTILITY in zone_names

    def test_zones_within_farm_bounds(self):
        """All zone boundaries must be inside the farm walls."""
        for tier in range(1, len(FARM_TIERS) + 1):
            state = _make_state(tier=tier)
            zones = calculate_zones(state.farm)
            for zone in zones:
                assert zone.x1 >= 1, f"Tier {tier} zone {zone.name} x1 in wall"
                assert zone.y1 >= 1, f"Tier {tier} zone {zone.name} y1 in wall"
                assert zone.x2 <= state.farm.width - 2, f"Tier {tier} zone {zone.name} x2 in wall"
                assert zone.y2 <= state.farm.height - 2, f"Tier {tier} zone {zone.name} y2 in wall"

    def test_zones_no_overlap(self):
        """Zone rectangles should not overlap."""
        for tier in range(1, len(FARM_TIERS) + 1):
            state = _make_state(tier=tier)
            zones = calculate_zones(state.farm)
            for i, z1 in enumerate(zones):
                for z2 in zones[i + 1:]:
                    # Two rectangles overlap if they overlap on both axes
                    x_overlap = z1.x1 <= z2.x2 and z2.x1 <= z1.x2
                    y_overlap = z1.y1 <= z2.y2 and z2.y1 <= z1.y2
                    assert not (x_overlap and y_overlap), (
                        f"Tier {tier}: zones {z1.name} and {z2.name} overlap"
                    )

    def test_zones_scale_with_farm_size(self):
        """Larger farms should have larger zones."""
        state_small = _make_state(tier=1)
        state_large = _make_state(tier=4)
        zones_small = calculate_zones(state_small.farm)
        zones_large = calculate_zones(state_large.farm)

        # Total zone area should be bigger for a larger farm
        area_small = sum(z.width * z.height for z in zones_small)
        area_large = sum(z.width * z.height for z in zones_large)
        assert area_large > area_small


class TestFacilityPlacement:
    """Tests for placement algorithm."""

    def test_single_facility_placed(self):
        """A single facility should be placed successfully."""
        state = _make_state(tier=3)
        _add_facility(state, FacilityType.FOOD_BOWL)

        placements, overflow = compute_arrangement(state)
        assert len(placements) == 1
        assert len(overflow) == 0

    def test_multiple_facility_types_grouped(self):
        """Different facility types should end up in different zones."""
        state = _make_state(tier=3)
        # Place facilities at arbitrary positions; arrange will reposition them
        food = _add_facility(state, FacilityType.FOOD_BOWL, 3, 3)
        water = _add_facility(state, FacilityType.WATER_BOTTLE, 5, 3)
        hideout = _add_facility(state, FacilityType.HIDEOUT, 7, 3)

        placements, overflow = compute_arrangement(state)
        assert len(placements) == 3
        assert len(overflow) == 0

        zones = calculate_zones(state.farm)
        zone_by_name = {z.name: z for z in zones}

        for p in placements:
            if p.facility.id == food.id:
                z = zone_by_name[ZONE_FEEDING]
                assert z.x1 <= p.new_x <= z.x2
                assert z.y1 <= p.new_y <= z.y2
            elif p.facility.id == water.id:
                z = zone_by_name[ZONE_HYDRATION]
                assert z.x1 <= p.new_x <= z.x2
                assert z.y1 <= p.new_y <= z.y2

    def test_no_facility_overlap(self):
        """Placed facilities must not overlap each other."""
        state = _make_state(tier=3)
        for i in range(5):
            _add_facility(state, FacilityType.FOOD_BOWL, 2 + i * 3, 3)

        placements, _ = compute_arrangement(state)
        occupied: set[tuple[int, int]] = set()
        for p in placements:
            info = FACILITY_INFO[p.facility.facility_type]
            for dx in range(info.size.width):
                for dy in range(info.size.height):
                    cell = (p.new_x + dx, p.new_y + dy)
                    assert cell not in occupied, f"Overlap at {cell}"
                    occupied.add(cell)

    def test_interaction_points_inside_farm(self):
        """All interaction points must be inside the farm (not in wall row)."""
        state = _make_state(tier=3)
        _add_facility(state, FacilityType.HIDEOUT, 5, 3)
        _add_facility(state, FacilityType.FOOD_BOWL, 10, 3)

        placements, _ = compute_arrangement(state)
        for p in placements:
            info = FACILITY_INFO[p.facility.facility_type]
            interaction_y = p.new_y + info.size.height
            assert interaction_y < state.farm.height - 1, (
                f"{p.facility.facility_type.value} interaction point at y={interaction_y} "
                f"is in wall (farm height={state.farm.height})"
            )

    def test_state_preserved_after_apply(self):
        """Facility state (current_amount, level, auto_refill) is preserved."""
        state = _make_state(tier=3)
        facility = _add_facility(state, FacilityType.FOOD_BOWL, 5, 3)
        facility.current_amount = 42.5
        facility.level = 2
        facility.auto_refill = True

        placements, overflow = compute_arrangement(state)
        apply_arrangement(state, placements, overflow)

        # Facility should still exist with same state
        f = state.get_facility(facility.id)
        assert f is not None
        assert f.current_amount == 42.5
        assert f.level == 2
        assert f.auto_refill is True

    def test_apply_updates_grid(self):
        """After apply, facility cells on the grid match new positions."""
        state = _make_state(tier=3)
        facility = _add_facility(state, FacilityType.FOOD_BOWL, 5, 3)

        placements, overflow = compute_arrangement(state)
        apply_arrangement(state, placements, overflow)

        p = placements[0]
        # New cells should be marked on grid
        for dx in range(facility.width):
            for dy in range(facility.height):
                cell = state.farm.get_cell(p.new_x + dx, p.new_y + dy)
                assert cell.facility_id == facility.id
                assert cell.is_walkable is False


class TestPigNavigation:
    """Tests for pig navigation cleanup."""

    def test_pig_paths_cleared(self):
        """All pig navigation state should be cleared."""
        state = _make_state(tier=3)
        pig = _make_pig(10.0, 10.0)
        pig.path = [(10, 10), (11, 10), (12, 10)]
        pig.target_position = Position(x=12.0, y=10.0)
        pig.target_facility_id = _add_facility(state, FacilityType.FOOD_BOWL, 12, 9).id
        pig.target_description = "eating at Food Bowl"
        pig.behavior_state = BehaviorState.EATING
        state.add_guinea_pig(pig)

        clear_pig_navigation(state)

        assert pig.path == []
        assert pig.target_position is None
        assert pig.target_facility_id is None
        assert pig.target_description is None
        assert pig.behavior_state == BehaviorState.IDLE

    def test_pig_relocated_from_unwalkable(self):
        """Pigs standing on facility cells should be moved to walkable cells."""
        state = _make_state(tier=3)
        facility = _add_facility(state, FacilityType.HIDEOUT, 10, 5)

        # Place pig on a facility cell
        pig = _make_pig(10.0, 5.0)
        state.add_guinea_pig(pig)

        clear_pig_navigation(state)

        # Pig should have been moved to a walkable cell
        gx, gy = pig.position.grid_pos()
        assert state.farm.is_walkable(gx, gy)


class TestOverflow:
    """Tests for overflow handling."""

    def test_overflow_on_tiny_farm(self):
        """Many large facilities on a small farm should produce overflow."""
        state = _make_state(tier=1)
        # Hideouts are 3x2, tier 1 farm is 30x15 — try to pack many
        for i in range(15):
            # Place at unique positions so they get added to state
            x = 2 + (i % 5) * 4
            y = 2 + (i // 5) * 4
            if x + 3 < state.farm.width - 1 and y + 2 < state.farm.height - 1:
                _add_facility(state, FacilityType.HIDEOUT, x, y)

        placements, overflow = compute_arrangement(state)
        # At least some should be placed
        assert len(placements) > 0
        # Total placed + overflow should equal total facilities
        assert len(placements) + len(overflow) == len(state.get_facilities_list())

    def test_overflow_no_overlap_with_first_pass(self):
        """Overflow facilities must not land on top of first-pass placements."""
        state = _make_state(tier=1)
        # Fill the rest zone with hideouts (3x2) so some overflow into feeding
        for i in range(8):
            x = 2 + (i % 4) * 4
            y = 2 + (i // 4) * 3
            if x + 3 < state.farm.width - 1 and y + 2 < state.farm.height - 1:
                _add_facility(state, FacilityType.HIDEOUT, x, y)
        # Also add food bowls that occupy the feeding zone
        for i in range(4):
            x = 2 + i * 4
            y = 2 + (8 // 4) * 3 + 3
            if x + 2 < state.farm.width - 1 and y + 1 < state.farm.height - 1:
                _add_facility(state, FacilityType.FOOD_BOWL, x, y)

        placements, _ = compute_arrangement(state)
        occupied: set[tuple[int, int]] = set()
        for p in placements:
            info = FACILITY_INFO[p.facility.facility_type]
            for dx in range(info.size.width):
                for dy in range(info.size.height):
                    cell = (p.new_x + dx, p.new_y + dy)
                    assert cell not in occupied, (
                        f"Overlap at {cell} — {p.facility.facility_type.value}"
                    )
                    occupied.add(cell)

    def test_many_mixed_facilities_no_overlap(self):
        """Realistic mix of many facilities: grid cells must never overlap."""
        state = _make_state(tier=4)  # Tier 4 (60x30) has room for 16 facilities
        types_and_positions = [
            (FacilityType.FOOD_BOWL, 2, 2),
            (FacilityType.FOOD_BOWL, 5, 2),
            (FacilityType.FOOD_BOWL, 8, 2),
            (FacilityType.HAY_RACK, 11, 2),
            (FacilityType.WATER_BOTTLE, 14, 2),
            (FacilityType.WATER_BOTTLE, 16, 2),
            (FacilityType.WATER_BOTTLE, 18, 2),
            (FacilityType.HIDEOUT, 2, 5),
            (FacilityType.HIDEOUT, 6, 5),
            (FacilityType.EXERCISE_WHEEL, 10, 5),
            (FacilityType.TUNNEL, 13, 5),
            (FacilityType.PLAY_AREA, 17, 5),
            (FacilityType.BREEDING_DEN, 2, 9),
            (FacilityType.NURSERY, 5, 9),
            (FacilityType.GROOMING_STATION, 9, 9),
            (FacilityType.VEGGIE_GARDEN, 12, 9),
        ]
        for ftype, x, y in types_and_positions:
            _add_facility(state, ftype, x, y)

        placements, overflow = compute_arrangement(state)
        assert len(overflow) == 0, f"{len(overflow)} facilities couldn't fit"

        occupied: set[tuple[int, int]] = set()
        for p in placements:
            info = FACILITY_INFO[p.facility.facility_type]
            for dx in range(info.size.width):
                for dy in range(info.size.height):
                    cell = (p.new_x + dx, p.new_y + dy)
                    assert cell not in occupied, (
                        f"Overlap at {cell} — {p.facility.facility_type.value}"
                    )
                    occupied.add(cell)


def _assert_no_sprite_overlap(state: GameState) -> None:
    """Assert no two facilities' sprites visually overlap."""
    from big_pig_farm.data.sprites import get_facility_sprite

    occupied: set[tuple[int, int]] = set()
    for f in state.get_facilities_list():
        sprite = get_facility_sprite(f.facility_type.value)
        for dy, line in enumerate(sprite):
            for dx in range(len(line)):
                cell = (f.position_x + dx, f.position_y + dy)
                assert cell not in occupied, (
                    f"Sprite overlap at {cell} — {f.facility_type.value}"
                )
                occupied.add(cell)


def _assert_no_overlap_in_state(state: GameState) -> None:
    """Assert no two facilities in state share any grid cell."""
    occupied: set[tuple[int, int]] = set()
    for f in state.get_facilities_list():
        for cell in f.cells:
            assert cell not in occupied, (
                f"Cell {cell} claimed by {f.facility_type.value} "
                f"but already occupied"
            )
            occupied.add(cell)


def _assert_grid_consistent(state: GameState) -> None:
    """Assert every facility's cells are registered on the grid."""
    for f in state.get_facilities_list():
        for cx, cy in f.cells:
            cell = state.farm.get_cell(cx, cy)
            assert cell is not None, f"Cell ({cx},{cy}) out of bounds"
            assert cell.facility_id == f.id, (
                f"Grid cell ({cx},{cy}) has facility_id={cell.facility_id} "
                f"but expected {f.id} ({f.facility_type.value})"
            )
            assert not cell.is_walkable, (
                f"Grid cell ({cx},{cy}) should not be walkable "
                f"(occupied by {f.facility_type.value})"
            )


class TestIntegration:
    """End-to-end tests: compute + apply + verify state and grid."""

    def test_full_cycle_no_overlap(self):
        """After compute+apply, no facility cells overlap in state."""
        state = _make_state(tier=3)
        for i in range(4):
            _add_facility(state, FacilityType.FOOD_BOWL, 2 + i * 3, 3)
        for i in range(3):
            _add_facility(state, FacilityType.WATER_BOTTLE, 2 + i * 2, 7)
        _add_facility(state, FacilityType.HIDEOUT, 2, 10)
        _add_facility(state, FacilityType.EXERCISE_WHEEL, 8, 10)
        _add_facility(state, FacilityType.BREEDING_DEN, 14, 10)

        placements, overflow = compute_arrangement(state)
        apply_arrangement(state, placements, overflow)

        _assert_no_overlap_in_state(state)
        _assert_grid_consistent(state)
        _assert_no_sprite_overlap(state)

    def test_full_cycle_all_tiers(self):
        """Auto-arrange works across all farm tiers without overlap."""
        facility_types = [
            FacilityType.FOOD_BOWL,
            FacilityType.WATER_BOTTLE,
            FacilityType.HIDEOUT,
            FacilityType.EXERCISE_WHEEL,
            FacilityType.BREEDING_DEN,
        ]
        for tier in range(1, len(FARM_TIERS) + 1):
            state = _make_state(tier=tier)
            for i, ftype in enumerate(facility_types):
                x = 2 + i * 4
                y = 3
                if x + 3 < state.farm.width - 1:
                    _add_facility(state, ftype, x, y)

            placements, overflow = compute_arrangement(state)
            apply_arrangement(state, placements, overflow)

            _assert_no_overlap_in_state(state)
            _assert_grid_consistent(state)

    def test_full_cycle_with_overflow(self):
        """Overflow facilities must still end up on the grid without grid overlap."""
        state = _make_state(tier=1)
        # Pack many hideouts (3x2) to force overflow
        for i in range(10):
            x = 2 + (i % 5) * 4
            y = 2 + (i // 5) * 3
            if x + 3 < state.farm.width - 1 and y + 2 < state.farm.height - 1:
                _add_facility(state, FacilityType.HIDEOUT, x, y)

        total = len(state.get_facilities_list())
        placements, overflow = compute_arrangement(state)
        apply_arrangement(state, placements, overflow)

        _assert_no_overlap_in_state(state)
        _assert_grid_consistent(state)
        # Note: sprite overlap may occur on very crowded small farms
        # (last-resort grid-only fallback), but grid integrity must hold
        assert len(state.get_facilities_list()) == total

    def test_full_cycle_16_mixed_facilities(self):
        """Realistic 16-facility mix: compute + apply + verify."""
        state = _make_state(tier=4)  # Tier 4 (60x30) — tier 3 too small for 16 sprites
        types_and_positions = [
            (FacilityType.FOOD_BOWL, 2, 2),
            (FacilityType.FOOD_BOWL, 5, 2),
            (FacilityType.FOOD_BOWL, 8, 2),
            (FacilityType.HAY_RACK, 11, 2),
            (FacilityType.WATER_BOTTLE, 14, 2),
            (FacilityType.WATER_BOTTLE, 16, 2),
            (FacilityType.WATER_BOTTLE, 18, 2),
            (FacilityType.HIDEOUT, 2, 5),
            (FacilityType.HIDEOUT, 6, 5),
            (FacilityType.EXERCISE_WHEEL, 10, 5),
            (FacilityType.TUNNEL, 13, 5),
            (FacilityType.PLAY_AREA, 17, 5),
            (FacilityType.BREEDING_DEN, 2, 9),
            (FacilityType.NURSERY, 5, 9),
            (FacilityType.GROOMING_STATION, 9, 9),
            (FacilityType.VEGGIE_GARDEN, 12, 9),
        ]
        for ftype, x, y in types_and_positions:
            _add_facility(state, ftype, x, y)

        placements, overflow = compute_arrangement(state)
        apply_arrangement(state, placements, overflow)

        _assert_no_overlap_in_state(state)
        _assert_grid_consistent(state)
        _assert_no_sprite_overlap(state)


class TestEmptyFarm:
    """Tests for edge cases."""

    def test_empty_farm_noop(self):
        """No facilities means no placements."""
        state = _make_state(tier=3)
        placements, overflow = compute_arrangement(state)
        assert placements == []
        assert overflow == []

    def test_small_farm_zone_collapse(self):
        """On small farms, hydration merges into feeding zone."""
        state = _make_state(tier=1)
        water = _add_facility(state, FacilityType.WATER_BOTTLE, 5, 3)

        placements, _ = compute_arrangement(state)
        assert len(placements) == 1

        zones = calculate_zones(state.farm)
        feeding_zone = next(z for z in zones if z.name == ZONE_FEEDING)

        p = placements[0]
        assert feeding_zone.x1 <= p.new_x <= feeding_zone.x2
        assert feeding_zone.y1 <= p.new_y <= feeding_zone.y2
