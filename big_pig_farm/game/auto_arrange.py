"""Auto-arrange facilities into logical zones after farm expansion."""

from dataclasses import dataclass
from typing import Optional

from big_pig_farm.data.config import AUTO_ARRANGE, FARM_TIERS
from big_pig_farm.data.sprites import get_facility_sprite
from big_pig_farm.entities.facilities import Facility, FacilityType, FACILITY_INFO
from big_pig_farm.entities.guinea_pig import BehaviorState
from big_pig_farm.game.state import GameState
from big_pig_farm.game.world import FarmGrid


# Zone names for organizing facilities
ZONE_FEEDING = "feeding"
ZONE_HYDRATION = "hydration"
ZONE_REST = "rest"
ZONE_PLAY = "play"
ZONE_UTILITY = "utility"

# Map facility types to their preferred zone
FACILITY_ZONE_MAP: dict[FacilityType, str] = {
    FacilityType.FOOD_BOWL: ZONE_FEEDING,
    FacilityType.HAY_RACK: ZONE_FEEDING,
    FacilityType.VEGGIE_GARDEN: ZONE_FEEDING,
    FacilityType.WATER_BOTTLE: ZONE_HYDRATION,
    FacilityType.HIDEOUT: ZONE_REST,
    FacilityType.EXERCISE_WHEEL: ZONE_PLAY,
    FacilityType.TUNNEL: ZONE_PLAY,
    FacilityType.PLAY_AREA: ZONE_PLAY,
    FacilityType.BREEDING_DEN: ZONE_UTILITY,
    FacilityType.NURSERY: ZONE_UTILITY,
    FacilityType.GROOMING_STATION: ZONE_UTILITY,
    FacilityType.GENETICS_LAB: ZONE_UTILITY,
}


@dataclass
class Zone:
    """A rectangular region of the farm for placing a category of facilities."""
    name: str
    x1: int  # Left boundary (inclusive)
    y1: int  # Top boundary (inclusive)
    x2: int  # Right boundary (inclusive)
    y2: int  # Bottom boundary (inclusive)

    @property
    def width(self) -> int:
        return self.x2 - self.x1 + 1

    @property
    def height(self) -> int:
        return self.y2 - self.y1 + 1


@dataclass
class Placement:
    """A computed facility placement."""
    facility: Facility
    new_x: int
    new_y: int


def _sprite_size(facility_type: FacilityType) -> tuple[int, int]:
    """Get the visual sprite dimensions (width, height) for a facility type."""
    sprite = get_facility_sprite(facility_type.value)
    sw = max(len(line) for line in sprite) if sprite else 1
    sh = len(sprite) if sprite else 1
    return sw, sh


def _is_small_farm(farm: FarmGrid) -> bool:
    """Check if the farm is small enough to use collapsed zones."""
    return (farm.width < AUTO_ARRANGE.SMALL_FARM_THRESHOLD_W
            or farm.height < AUTO_ARRANGE.SMALL_FARM_THRESHOLD_H)


def calculate_zones(farm: FarmGrid) -> list[Zone]:
    """Calculate zone boundaries based on farm dimensions.

    Normal layout (5 zones):
        +----------------------------+
        | FEEDING      | REST        |
        |              |             |
        | HYDRATION    | PLAY        |
        |              |             |
        | UTILITY (full width)       |
        +----------------------------+

    Small farm layout (3 zones):
        +----------------------------+
        | FEEDING+HYDRATION | REST+PLAY |
        |                   |           |
        | UTILITY (full width)          |
        +----------------------------+
    """
    # Interior boundaries (inside walls)
    ix1 = 1
    iy1 = 1
    ix2 = farm.width - 2
    iy2 = farm.height - 2
    iw = ix2 - ix1 + 1
    ih = iy2 - iy1 + 1

    margin = AUTO_ARRANGE.ZONE_MARGIN

    if _is_small_farm(farm):
        # 3-zone layout: left | right | bottom
        mid_x = ix1 + iw // 2
        # 70% top, 30% bottom
        split_y = iy1 + int(ih * 0.7)

        return [
            Zone(ZONE_FEEDING, ix1 + margin, iy1 + margin,
                 mid_x - 1 - margin, split_y - 1 - margin),
            Zone(ZONE_REST, mid_x + margin, iy1 + margin,
                 ix2 - margin, split_y - 1 - margin),
            Zone(ZONE_UTILITY, ix1 + margin, split_y + margin,
                 ix2 - margin, iy2 - margin),
        ]
    else:
        # 5-zone layout
        mid_x = ix1 + iw // 2
        # Top/middle split at 40%, bottom at 80%
        split_y1 = iy1 + int(ih * 0.4)
        split_y2 = iy1 + int(ih * 0.8)

        return [
            Zone(ZONE_FEEDING, ix1 + margin, iy1 + margin,
                 mid_x - 1 - margin, split_y1 - 1 - margin),
            Zone(ZONE_REST, mid_x + margin, iy1 + margin,
                 ix2 - margin, split_y1 - 1 - margin),
            Zone(ZONE_HYDRATION, ix1 + margin, split_y1 + margin,
                 mid_x - 1 - margin, split_y2 - 1 - margin),
            Zone(ZONE_PLAY, mid_x + margin, split_y1 + margin,
                 ix2 - margin, split_y2 - 1 - margin),
            Zone(ZONE_UTILITY, ix1 + margin, split_y2 + margin,
                 ix2 - margin, iy2 - margin),
        ]


def _get_zone_for_facility(
    facility_type: FacilityType,
    is_small: bool,
) -> str:
    """Get the preferred zone name for a facility type.

    On small farms, hydration merges into feeding and play merges into rest.
    """
    zone = FACILITY_ZONE_MAP.get(facility_type, ZONE_UTILITY)
    if is_small:
        if zone == ZONE_HYDRATION:
            return ZONE_FEEDING
        if zone == ZONE_PLAY:
            return ZONE_REST
    return zone


def _place_facilities_in_zone(
    facilities: list[Facility],
    zone: Zone,
    h_gap: int,
    v_gap: int,
    farm_height: int,
    occupied: set[tuple[int, int]],
) -> tuple[list[Placement], list[Facility]]:
    """Place facilities within a zone using greedy left-to-right, top-to-bottom.

    The `occupied` set is shared across all zone placements and is updated
    in-place to prevent cross-zone and overflow-pass collisions.

    Returns (placed, overflow) where overflow couldn't fit in the zone.
    """
    # Sort largest-first by sprite area (visual footprint determines packing)
    sorted_facilities = sorted(
        facilities,
        key=lambda f: (_sprite_size(f.facility_type)[0] * _sprite_size(f.facility_type)[1]),
        reverse=True,
    )

    placed: list[Placement] = []
    overflow: list[Facility] = []

    for facility in sorted_facilities:
        info = FACILITY_INFO[facility.facility_type]
        fw = info.size.width
        fh = info.size.height
        # Interaction point is at position_y + height, must be inside walls
        interaction_row = fh  # relative offset

        # Sprite dimensions determine visual footprint (much larger than grid)
        sw, sh = _sprite_size(facility.facility_type)

        placement_found = False

        # Scan top-to-bottom, left-to-right
        y = zone.y1
        while y + fh - 1 <= zone.y2 and not placement_found:
            # Ensure interaction point row is inside the farm (not in wall)
            if y + interaction_row >= farm_height - 1:
                y += 1
                continue

            x = zone.x1
            while x + fw - 1 <= zone.x2 and not placement_found:
                # Check the sprite footprint is clear (not just grid cells)
                cells_ok = True
                for dx in range(sw):
                    for dy in range(sh):
                        if (x + dx, y + dy) in occupied:
                            cells_ok = False
                            break
                    if not cells_ok:
                        break

                if cells_ok:
                    # Place it
                    placed.append(Placement(facility, x, y))
                    # Mark sprite footprint + gap as occupied
                    for dx in range(-1, sw + h_gap):
                        for dy in range(-1, sh + v_gap):
                            occupied.add((x + dx, y + dy))
                    placement_found = True

                x += 1
            y += 1

        if not placement_found:
            overflow.append(facility)

    return placed, overflow


def compute_arrangement(
    state: GameState,
) -> tuple[list[Placement], list[Facility]]:
    """Compute new positions for all facilities without mutating state.

    Returns (placements, overflow) where overflow facilities couldn't fit.
    """
    facilities = state.get_facilities_list()
    if not facilities:
        return [], []

    farm = state.farm
    is_small = _is_small_farm(farm)
    zones = calculate_zones(farm)

    if is_small:
        h_gap = AUTO_ARRANGE.SMALL_HORIZONTAL_GAP
        v_gap = AUTO_ARRANGE.SMALL_VERTICAL_GAP
    else:
        h_gap = AUTO_ARRANGE.HORIZONTAL_GAP
        v_gap = AUTO_ARRANGE.VERTICAL_GAP

    # Group facilities by zone
    zone_facilities: dict[str, list[Facility]] = {z.name: [] for z in zones}
    for facility in facilities:
        zone_name = _get_zone_for_facility(facility.facility_type, is_small)
        if zone_name in zone_facilities:
            zone_facilities[zone_name].append(facility)
        else:
            # Unknown zone, put in utility (last zone)
            zone_facilities[zones[-1].name].append(facility)

    all_placed: list[Placement] = []
    all_overflow: list[Facility] = []

    # Single shared set prevents cross-zone and overflow-pass collisions
    occupied: set[tuple[int, int]] = set()

    for zone in zones:
        zone_facs = zone_facilities.get(zone.name, [])
        if not zone_facs:
            continue
        placed, overflow = _place_facilities_in_zone(
            zone_facs, zone, h_gap, v_gap, farm.height, occupied,
        )
        all_placed.extend(placed)
        all_overflow.extend(overflow)

    # Try to place overflow in any zone with remaining space
    if all_overflow:
        for zone in zones:
            if not all_overflow:
                break
            placed, still_overflow = _place_facilities_in_zone(
                all_overflow, zone, h_gap, v_gap, farm.height, occupied,
            )
            all_placed.extend(placed)
            all_overflow = still_overflow

    return all_placed, all_overflow


def _find_grid_position(
    farm: FarmGrid,
    facility: Facility,
    occupied: set[tuple[int, int]],
) -> bool:
    """Scan the grid for a position that is valid on the grid AND sprite-clear.

    Brute-force fallback for overflow facilities. Uses tight packing (no gap)
    to maximize chances of fitting. If sprite-aware placement fails entirely,
    falls back to grid-only placement as a last resort.
    Updates `occupied` in-place on success. Returns True if placed.
    """
    fw = facility.width
    fh = facility.height
    sw, sh = _sprite_size(facility.facility_type)

    # First pass: sprite-aware (tight, no gap)
    for y in range(1, farm.height - fh - 1):
        for x in range(1, farm.width - fw):
            sprite_ok = True
            for dx in range(sw):
                for dy in range(sh):
                    if (x + dx, y + dy) in occupied:
                        sprite_ok = False
                        break
                if not sprite_ok:
                    break
            if not sprite_ok:
                continue

            facility.position_x = x
            facility.position_y = y
            if farm.place_facility(facility):
                for dx in range(sw):
                    for dy in range(sh):
                        occupied.add((x + dx, y + dy))
                return True

    # Last resort: grid-only (visual overlap possible, but facility is placed)
    for y in range(1, farm.height - fh - 1):
        for x in range(1, farm.width - fw):
            facility.position_x = x
            facility.position_y = y
            if farm.place_facility(facility):
                for dx in range(sw):
                    for dy in range(sh):
                        occupied.add((x + dx, y + dy))
                return True
    return False


def apply_arrangement(
    state: GameState,
    placements: list[Placement],
    overflow: list[Facility],
) -> None:
    """Remove all facilities from the grid, reposition, and re-place them.

    Preserves facility state (current_amount, level, auto_refill, etc).
    Overflow facilities that couldn't fit in zones are placed at the first
    available grid position, respecting sprite-level spacing.
    """
    farm = state.farm
    is_small = _is_small_farm(farm)

    if is_small:
        h_gap = AUTO_ARRANGE.SMALL_HORIZONTAL_GAP
        v_gap = AUTO_ARRANGE.SMALL_VERTICAL_GAP
    else:
        h_gap = AUTO_ARRANGE.HORIZONTAL_GAP
        v_gap = AUTO_ARRANGE.VERTICAL_GAP

    # Remove all facilities from the grid (but keep in state.facilities dict)
    for facility in state.get_facilities_list():
        farm.remove_facility(facility)

    # Build sprite-aware occupied set from computed placements
    occupied: set[tuple[int, int]] = set()

    # Apply new positions and re-place on grid
    for placement in placements:
        facility = placement.facility
        facility.position_x = placement.new_x
        facility.position_y = placement.new_y
        sw, sh = _sprite_size(facility.facility_type)

        # Verify sprite footprint is still clear (a prior fallback placement
        # may have occupied cells near this computed position)
        sprite_clear = all(
            (placement.new_x + dx, placement.new_y + dy) not in occupied
            for dx in range(sw) for dy in range(sh)
        )

        if sprite_clear and farm.place_facility(facility):
            # Mark sprite footprint + gap as occupied
            for dx in range(-1, sw + h_gap):
                for dy in range(-1, sh + v_gap):
                    occupied.add((placement.new_x + dx, placement.new_y + dy))
        else:
            # Computed position collided — find any valid position
            _find_grid_position(farm, facility, occupied)

    # Place overflow facilities at whatever positions are still free
    for facility in overflow:
        _find_grid_position(farm, facility, occupied)


def clear_pig_navigation(state: GameState) -> None:
    """Reset all pig navigation state and relocate pigs on unwalkable cells."""
    farm = state.farm

    for pig in state.get_pigs_list():
        pig.path = []
        pig.target_position = None
        pig.target_facility_id = None
        pig.target_description = None
        pig.behavior_state = BehaviorState.IDLE

        # If pig is standing on an unwalkable cell, move to nearest walkable
        gx, gy = pig.position.grid_pos()
        if not farm.is_walkable(gx, gy):
            new_pos = farm._find_nearest_walkable((gx, gy))
            if new_pos:
                pig.position.x = float(new_pos[0])
                pig.position.y = float(new_pos[1])
