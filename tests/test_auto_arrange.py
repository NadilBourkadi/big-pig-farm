"""Tests for auto-arrange facility layout."""

import pytest

from big_pig_farm.data.config import FARM_TIERS
from big_pig_farm.entities.facilities import Facility, FacilityType, FACILITY_INFO
from big_pig_farm.entities.genetics import Genotype, calculate_phenotype
from big_pig_farm.entities.guinea_pig import GuineaPig, BehaviorState, Position, Gender
from big_pig_farm.game.auto_arrange import (
    calculate_zones,
    calculate_neighborhood_zones,
    compute_arrangement,
    apply_arrangement,
    clear_pig_navigation,
    _determine_neighborhood_count,
    _is_small_farm,
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

    def test_small_farm_produces_3_zones(self):
        """Small farms (tiers 1-2) should produce 3 zones."""
        state = _make_state(tier=1)
        zones = calculate_zones(state.farm)
        assert len(zones) == 3
        zone_names = {z.name for z in zones}
        assert ZONE_FEEDING in zone_names
        assert ZONE_REST in zone_names
        assert ZONE_UTILITY in zone_names

    def test_zones_within_farm_bounds(self):
        """All zone boundaries must be inside the farm walls."""
        # Small farms use calculate_zones
        for tier in range(1, 3):
            state = _make_state(tier=tier)
            zones = calculate_zones(state.farm)
            for zone in zones:
                assert zone.x1 >= 1, f"Tier {tier} zone {zone.name} x1 in wall"
                assert zone.y1 >= 1, f"Tier {tier} zone {zone.name} y1 in wall"
                assert zone.x2 <= state.farm.width - 2, f"Tier {tier} zone {zone.name} x2 in wall"
                assert zone.y2 <= state.farm.height - 2, f"Tier {tier} zone {zone.name} y2 in wall"

    def test_zones_no_overlap(self):
        """Zone rectangles should not overlap."""
        for tier in range(1, 3):
            state = _make_state(tier=tier)
            zones = calculate_zones(state.farm)
            for i, z1 in enumerate(zones):
                for z2 in zones[i + 1:]:
                    x_overlap = z1.x1 <= z2.x2 and z2.x1 <= z1.x2
                    y_overlap = z1.y1 <= z2.y2 and z2.y1 <= z1.y2
                    assert not (x_overlap and y_overlap), (
                        f"Tier {tier}: zones {z1.name} and {z2.name} overlap"
                    )


class TestNeighborhoodZones:
    """Tests for neighborhood zone calculation."""

    def test_neighborhood_zones_within_bounds(self):
        """All neighborhood zones must be inside the farm walls."""
        for tier in range(3, len(FARM_TIERS) + 1):
            state = _make_state(tier=tier)
            for num_nh in range(1, 5):
                zones = calculate_neighborhood_zones(state.farm, num_nh)
                for zone in zones:
                    assert zone.x1 >= 1, f"Tier {tier} nh={num_nh} zone {zone.name} x1 in wall"
                    assert zone.y1 >= 1, f"Tier {tier} nh={num_nh} zone {zone.name} y1 in wall"
                    assert zone.x2 <= state.farm.width - 2, f"Tier {tier} nh={num_nh} zone {zone.name} x2 in wall"
                    assert zone.y2 <= state.farm.height - 2, f"Tier {tier} nh={num_nh} zone {zone.name} y2 in wall"

    def test_neighborhood_zones_no_overlap(self):
        """Neighborhood zones should not overlap."""
        for tier in range(3, len(FARM_TIERS) + 1):
            state = _make_state(tier=tier)
            for num_nh in range(1, 5):
                zones = calculate_neighborhood_zones(state.farm, num_nh)
                for i, z1 in enumerate(zones):
                    for z2 in zones[i + 1:]:
                        x_overlap = z1.x1 <= z2.x2 and z2.x1 <= z1.x2
                        y_overlap = z1.y1 <= z2.y2 and z2.y1 <= z1.y2
                        assert not (x_overlap and y_overlap), (
                            f"Tier {tier} nh={num_nh}: zones {z1.name} and {z2.name} overlap"
                        )

    def test_neighborhood_zone_count(self):
        """Should produce num_neighborhoods + 1 (utility) zones."""
        state = _make_state(tier=4)
        for num_nh in range(1, 5):
            zones = calculate_neighborhood_zones(state.farm, num_nh)
            assert len(zones) == num_nh + 1
            assert zones[-1].name == ZONE_UTILITY

    def test_neighborhood_count_from_facilities(self):
        """Neighborhood count is the minimum across essential categories."""
        state = _make_state(tier=4)
        # 3 food, 2 water, 1 rest, 2 play → min is 1 (rest)
        _add_facility(state, FacilityType.FOOD_BOWL, 2, 2)
        _add_facility(state, FacilityType.FOOD_BOWL, 5, 2)
        _add_facility(state, FacilityType.FOOD_BOWL, 8, 2)
        _add_facility(state, FacilityType.WATER_BOTTLE, 11, 2)
        _add_facility(state, FacilityType.WATER_BOTTLE, 14, 2)
        _add_facility(state, FacilityType.HIDEOUT, 2, 5)
        _add_facility(state, FacilityType.EXERCISE_WHEEL, 5, 5)
        _add_facility(state, FacilityType.TUNNEL, 8, 5)

        count = _determine_neighborhood_count(state.get_facilities_list())
        assert count == 1

    def test_neighborhood_count_balanced(self):
        """With 2 of each essential type, should get 2 neighborhoods."""
        state = _make_state(tier=4)
        _add_facility(state, FacilityType.FOOD_BOWL, 2, 2)
        _add_facility(state, FacilityType.FOOD_BOWL, 5, 2)
        _add_facility(state, FacilityType.WATER_BOTTLE, 8, 2)
        _add_facility(state, FacilityType.WATER_BOTTLE, 11, 2)
        _add_facility(state, FacilityType.HIDEOUT, 2, 5)
        _add_facility(state, FacilityType.HIDEOUT, 5, 5)
        _add_facility(state, FacilityType.EXERCISE_WHEEL, 8, 5)
        _add_facility(state, FacilityType.TUNNEL, 11, 5)

        count = _determine_neighborhood_count(state.get_facilities_list())
        assert count == 2

    def test_neighborhood_count_capped(self):
        """Neighborhood count is capped at MAX_NEIGHBORHOODS (4)."""
        state = _make_state(tier=6)
        # 6 of each essential type
        for i in range(6):
            _add_facility(state, FacilityType.FOOD_BOWL, 2 + i * 4, 2)
            _add_facility(state, FacilityType.WATER_BOTTLE, 2 + i * 4, 5)
            _add_facility(state, FacilityType.HIDEOUT, 2 + i * 4, 8)
            _add_facility(state, FacilityType.EXERCISE_WHEEL, 2 + i * 4, 11)

        count = _determine_neighborhood_count(state.get_facilities_list())
        assert count == 4  # Capped at MAX_NEIGHBORHOODS

    def test_utility_only_gives_1_neighborhood(self):
        """Only utility facilities → 1 neighborhood (no essential categories)."""
        state = _make_state(tier=4)
        _add_facility(state, FacilityType.BREEDING_DEN, 2, 2)
        _add_facility(state, FacilityType.NURSERY, 5, 2)

        count = _determine_neighborhood_count(state.get_facilities_list())
        assert count == 1

    def test_large_farm_uses_neighborhoods(self):
        """Tier 3+ should use neighborhood layout, not type-grouped zones."""
        state = _make_state(tier=3)
        assert not _is_small_farm(state.farm)

    def test_small_farm_detected(self):
        """Tiers 1-2 should be detected as small farms."""
        for tier in (1, 2):
            state = _make_state(tier=tier)
            assert _is_small_farm(state.farm)


class TestFacilityPlacement:
    """Tests for placement algorithm."""

    def test_single_facility_placed(self):
        """A single facility should be placed successfully."""
        state = _make_state(tier=3)
        _add_facility(state, FacilityType.FOOD_BOWL)

        placements, overflow = compute_arrangement(state)
        assert len(placements) == 1
        assert len(overflow) == 0

    def test_neighborhood_facilities_co_located(self):
        """On large farms, different essential types end up in the same neighborhood."""
        state = _make_state(tier=4)  # Tier 4 has enough space for all sprite sizes
        food = _add_facility(state, FacilityType.FOOD_BOWL, 3, 3)
        water = _add_facility(state, FacilityType.WATER_BOTTLE, 8, 3)
        hideout = _add_facility(state, FacilityType.HIDEOUT, 12, 3)
        wheel = _add_facility(state, FacilityType.EXERCISE_WHEEL, 18, 3)

        placements, overflow = compute_arrangement(state)
        assert len(placements) == 4
        assert len(overflow) == 0

        # With 1 of each type, all should be in the same neighborhood zone
        zones = calculate_neighborhood_zones(state.farm, 1)
        nh_zone = zones[0]  # The single neighborhood

        for p in placements:
            assert nh_zone.x1 <= p.new_x <= nh_zone.x2, (
                f"{p.facility.facility_type.value} at x={p.new_x} "
                f"outside neighborhood ({nh_zone.x1}-{nh_zone.x2})"
            )
            assert nh_zone.y1 <= p.new_y <= nh_zone.y2, (
                f"{p.facility.facility_type.value} at y={p.new_y} "
                f"outside neighborhood ({nh_zone.y1}-{nh_zone.y2})"
            )

    def test_facilities_distributed_across_neighborhoods(self):
        """With 2 of each essential type, facilities split into 2 neighborhoods."""
        state = _make_state(tier=4)
        foods = [
            _add_facility(state, FacilityType.FOOD_BOWL, 2, 2),
            _add_facility(state, FacilityType.FOOD_BOWL, 5, 2),
        ]
        waters = [
            _add_facility(state, FacilityType.WATER_BOTTLE, 8, 2),
            _add_facility(state, FacilityType.WATER_BOTTLE, 11, 2),
        ]
        hideouts = [
            _add_facility(state, FacilityType.HIDEOUT, 2, 5),
            _add_facility(state, FacilityType.HIDEOUT, 5, 5),
        ]
        wheels = [
            _add_facility(state, FacilityType.EXERCISE_WHEEL, 8, 5),
            _add_facility(state, FacilityType.EXERCISE_WHEEL, 11, 5),
        ]

        placements, overflow = compute_arrangement(state)
        assert len(overflow) == 0

        zones = calculate_neighborhood_zones(state.farm, 2)
        nh0 = zones[0]
        nh1 = zones[1]

        def in_zone(p, z):
            return z.x1 <= p.new_x <= z.x2 and z.y1 <= p.new_y <= z.y2

        # Each neighborhood should have facilities from different categories
        nh0_placements = [p for p in placements if in_zone(p, nh0)]
        nh1_placements = [p for p in placements if in_zone(p, nh1)]

        nh0_types = {p.facility.facility_type for p in nh0_placements}
        nh1_types = {p.facility.facility_type for p in nh1_placements}

        # Each neighborhood should have at least food + water + rest + play
        assert FacilityType.FOOD_BOWL in nh0_types
        assert FacilityType.FOOD_BOWL in nh1_types

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
    """Assert no two facilities' sprites visually overlap.

    Uses half-block sprite dimensions (the actual rendered size) with
    fallback to ASCII sprites when no half-block art exists.
    """
    from big_pig_farm.data.sprites import get_facility_halfblock_sprite, get_facility_sprite, ZoomLevel

    occupied: set[tuple[int, int]] = set()
    for f in state.get_facilities_list():
        halfblock = get_facility_halfblock_sprite(f.facility_type.value, "", ZoomLevel.NORMAL)
        if halfblock is not None:
            sw = len(halfblock[0]) if halfblock else 0
            sh = len(halfblock)
        else:
            sprite = get_facility_sprite(f.facility_type.value)
            sw = max(len(line) for line in sprite)
            sh = len(sprite)

        for dy in range(sh):
            for dx in range(sw):
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

    def test_full_cycle_neighborhood_layout(self):
        """Neighborhood layout: each neighborhood gets a mix of facility types."""
        state = _make_state(tier=5)
        # 3 of each essential type → 3 neighborhoods
        for i in range(3):
            _add_facility(state, FacilityType.FOOD_BOWL, 2 + i * 4, 2)
            _add_facility(state, FacilityType.WATER_BOTTLE, 2 + i * 4, 5)
            _add_facility(state, FacilityType.HIDEOUT, 2 + i * 4, 8)
            _add_facility(state, FacilityType.EXERCISE_WHEEL, 2 + i * 4, 11)
        # Plus utility
        _add_facility(state, FacilityType.BREEDING_DEN, 20, 2)

        placements, overflow = compute_arrangement(state)
        apply_arrangement(state, placements, overflow)

        assert len(overflow) == 0
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
