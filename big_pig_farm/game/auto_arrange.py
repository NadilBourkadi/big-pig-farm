"""Auto-arrange facilities into logical zones after farm expansion."""

from dataclasses import dataclass
from typing import Optional

from big_pig_farm.data.config import AUTO_ARRANGE, FARM_TIERS
from big_pig_farm.data.sprites import get_facility_halfblock_sprite, get_facility_sprite, ZoomLevel
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

# Map facility types to their preferred zone (used by small-farm layout)
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

# Essential need categories for neighborhood layout
ESSENTIAL_NEEDS = ("food", "water", "rest", "play")

# Map facility types to essential need categories (None = utility)
FACILITY_NEED_MAP: dict[FacilityType, Optional[str]] = {
    FacilityType.FOOD_BOWL: "food",
    FacilityType.HAY_RACK: "food",
    FacilityType.VEGGIE_GARDEN: "food",
    FacilityType.WATER_BOTTLE: "water",
    FacilityType.HIDEOUT: "rest",
    FacilityType.EXERCISE_WHEEL: "play",
    FacilityType.TUNNEL: "play",
    FacilityType.PLAY_AREA: "play",
    FacilityType.BREEDING_DEN: None,
    FacilityType.NURSERY: None,
    FacilityType.GROOMING_STATION: None,
    FacilityType.GENETICS_LAB: None,
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
    """Get the visual sprite dimensions (width, height) for a facility type.

    Uses the half-block sprite at normal zoom (the actual rendered size),
    falling back to the ASCII sprite if no half-block art exists.
    """
    halfblock = get_facility_halfblock_sprite(facility_type.value, "", ZoomLevel.NORMAL)
    if halfblock is not None:
        sh = len(halfblock)
        sw = len(halfblock[0]) if halfblock else 1
        return sw, sh
    sprite = get_facility_sprite(facility_type.value)
    sw = max(len(line) for line in sprite) if sprite else 1
    sh = len(sprite) if sprite else 1
    return sw, sh


def _is_small_farm(farm: FarmGrid) -> bool:
    """Check if the farm is small enough to use collapsed zones."""
    return (farm.width < AUTO_ARRANGE.SMALL_FARM_THRESHOLD_W
            or farm.height < AUTO_ARRANGE.SMALL_FARM_THRESHOLD_H)


def calculate_zones(farm: FarmGrid) -> list[Zone]:
    """Calculate zone boundaries for the small-farm (type-grouped) layout.

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


def _determine_neighborhood_count(facilities: list[Facility]) -> int:
    """Determine how many neighborhoods to create from facility distribution.

    Count facilities per essential need category and return the minimum,
    capped at MAX_NEIGHBORHOODS.
    """
    need_counts: dict[str, int] = {}
    for f in facilities:
        need = FACILITY_NEED_MAP.get(f.facility_type)
        if need is not None:
            need_counts[need] = need_counts.get(need, 0) + 1

    if not need_counts:
        return 1

    active_counts = list(need_counts.values())
    return min(min(active_counts), AUTO_ARRANGE.MAX_NEIGHBORHOODS)


def _neighborhood_grid(count: int, area_width: int, area_height: int) -> tuple[int, int]:
    """Determine (rows, cols) grid layout for neighborhood zones."""
    if count <= 1:
        return 1, 1
    elif count == 2:
        return (1, 2) if area_width >= area_height else (2, 1)
    elif count == 3:
        return (1, 3) if area_width >= area_height else (3, 1)
    else:
        return 2, 2


def calculate_neighborhood_zones(farm: FarmGrid, num_neighborhoods: int) -> list[Zone]:
    """Calculate neighborhood zones + utility zone for a large farm.

    Layout:
        +----------------------------+
        | Neighborhood 0 | Neigh. 1  |
        |                |           |
        | Neighborhood 2 | Neigh. 3  |
        |                |           |
        | UTILITY (full width)       |
        +----------------------------+
    """
    ix1 = 1
    iy1 = 1
    ix2 = farm.width - 2
    iy2 = farm.height - 2
    iw = ix2 - ix1 + 1
    ih = iy2 - iy1 + 1
    margin = AUTO_ARRANGE.ZONE_MARGIN

    # Reserve bottom fraction for utility
    utility_h = max(3, int(ih * AUTO_ARRANGE.NEIGHBORHOOD_UTILITY_FRACTION))
    utility_y = iy2 - utility_h + 1

    # Neighborhood area is everything above utility
    nh_y2 = utility_y - 1
    nh_h = nh_y2 - iy1 + 1

    rows, cols = _neighborhood_grid(num_neighborhoods, iw, nh_h)

    zones: list[Zone] = []
    col_w = iw // cols
    row_h = nh_h // rows

    idx = 0
    for r in range(rows):
        for c in range(cols):
            if idx >= num_neighborhoods:
                break
            x1 = ix1 + c * col_w
            y1 = iy1 + r * row_h
            # Last column/row extends to the edge to avoid rounding gaps
            x2 = (x1 + col_w - 1) if c < cols - 1 else ix2
            y2 = (y1 + row_h - 1) if r < rows - 1 else nh_y2
            zones.append(Zone(
                f"neighborhood_{idx}",
                x1 + margin, y1 + margin,
                x2 - margin, y2 - margin,
            ))
            idx += 1

    # Utility zone at the bottom
    zones.append(Zone(
        ZONE_UTILITY,
        ix1 + margin, utility_y + margin,
        ix2 - margin, iy2 - margin,
    ))

    return zones


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
    """Place facilities within a zone, spreading them evenly across the zone height.

    Facilities are assigned to horizontal shelves (rows) by packing left-to-right.
    Shelves are then distributed vertically to maximize spacing within the zone,
    preventing the top-heavy clustering of greedy top-to-bottom placement.

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

    # Phase 1: Assign facilities to horizontal shelves (left-to-right rows)
    # Each shelf: (items, max_sprite_height)
    # Each item: (facility, x_position, sprite_width, sprite_height)
    shelves: list[tuple[list[tuple[Facility, int, int, int]], int]] = []
    current_items: list[tuple[Facility, int, int, int]] = []
    cursor_x = zone.x1
    max_sprite_h = 0

    for facility in sorted_facilities:
        sw, sh = _sprite_size(facility.facility_type)

        # Facility sprite wider than zone — can't fit at all
        if sw > zone.width:
            overflow.append(facility)
            continue

        # Check if facility fits in current row
        if current_items and cursor_x + sw - 1 > zone.x2:
            shelves.append((current_items, max_sprite_h))
            current_items = []
            cursor_x = zone.x1
            max_sprite_h = 0

        current_items.append((facility, cursor_x, sw, sh))
        cursor_x += sw + h_gap
        max_sprite_h = max(max_sprite_h, sh)

    if current_items:
        shelves.append((current_items, max_sprite_h))

    if not shelves:
        return placed, overflow

    # Phase 2: Compute y-position for each shelf to spread evenly across zone
    num_shelves = len(shelves)
    total_content_h = sum(sh for _, sh in shelves)
    zone_h = zone.y2 - zone.y1 + 1

    if num_shelves == 1:
        # Single shelf: center vertically in the zone
        shelf_ys = [zone.y1 + (zone_h - shelves[0][1]) // 2]
    else:
        remaining_space = zone_h - total_content_h
        if remaining_space > 0:
            gap = max(v_gap, remaining_space // (num_shelves - 1))
        else:
            gap = v_gap

        total_needed = total_content_h + gap * (num_shelves - 1)
        if total_needed <= zone_h:
            start_y = zone.y1
        else:
            gap = v_gap
            start_y = zone.y1

        shelf_ys = []
        y = start_y
        for _, sh in shelves:
            shelf_ys.append(y)
            y += sh + gap

    # Phase 3: Place facilities at computed positions
    for (items, _), shelf_y in zip(shelves, shelf_ys):
        for facility, x, sw, sh in items:
            info = FACILITY_INFO[facility.facility_type]
            fh = info.size.height
            interaction_row = fh

            # Bounds check: facility grid cells within zone
            if shelf_y + fh - 1 > zone.y2:
                overflow.append(facility)
                continue

            # Interaction point must be inside the farm (not in wall)
            if shelf_y + interaction_row >= farm_height - 1:
                overflow.append(facility)
                continue

            # Check the sprite footprint is clear (not just grid cells)
            cells_ok = True
            for dx in range(sw):
                for dy in range(sh):
                    if (x + dx, shelf_y + dy) in occupied:
                        cells_ok = False
                        break
                if not cells_ok:
                    break

            if cells_ok:
                placed.append(Placement(facility, x, shelf_y))
                # Mark sprite footprint + gap as occupied
                for dx in range(-1, sw + h_gap):
                    for dy in range(-1, sh + v_gap):
                        occupied.add((x + dx, shelf_y + dy))
            else:
                overflow.append(facility)

    return placed, overflow


def _compute_small_farm_arrangement(
    facilities: list[Facility],
    farm: FarmGrid,
) -> tuple[list[Placement], list[Facility]]:
    """Compute arrangement using the small-farm 3-zone type-grouped layout."""
    zones = calculate_zones(farm)
    h_gap = AUTO_ARRANGE.SMALL_HORIZONTAL_GAP
    v_gap = AUTO_ARRANGE.SMALL_VERTICAL_GAP

    # Group facilities by zone
    zone_facilities: dict[str, list[Facility]] = {z.name: [] for z in zones}
    for facility in facilities:
        zone_name = _get_zone_for_facility(facility.facility_type, is_small=True)
        if zone_name in zone_facilities:
            zone_facilities[zone_name].append(facility)
        else:
            zone_facilities[zones[-1].name].append(facility)

    all_placed: list[Placement] = []
    all_overflow: list[Facility] = []
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


def _compute_neighborhood_arrangement(
    facilities: list[Facility],
    farm: FarmGrid,
) -> tuple[list[Placement], list[Facility]]:
    """Compute arrangement using neighborhood layout for large farms.

    Each neighborhood contains one of each essential facility type (food,
    water, rest, play). Pigs naturally use the nearest facility, so they
    self-organize by proximity instead of all running to the same zone.
    """
    h_gap = AUTO_ARRANGE.HORIZONTAL_GAP
    v_gap = AUTO_ARRANGE.VERTICAL_GAP

    # Classify facilities into essential needs vs utility
    essential: dict[str, list[Facility]] = {need: [] for need in ESSENTIAL_NEEDS}
    utility_facilities: list[Facility] = []

    for f in facilities:
        need = FACILITY_NEED_MAP.get(f.facility_type)
        if need is not None:
            essential[need].append(f)
        else:
            utility_facilities.append(f)

    # Determine neighborhood count and create zones
    num_neighborhoods = _determine_neighborhood_count(facilities)
    zones = calculate_neighborhood_zones(farm, num_neighborhoods)
    nh_zones = zones[:-1]  # All but utility
    utility_zone = zones[-1]

    # Distribute essential facilities round-robin across neighborhoods
    zone_facilities: dict[str, list[Facility]] = {z.name: [] for z in zones}
    for need in ESSENTIAL_NEEDS:
        for i, f in enumerate(essential[need]):
            zone_idx = i % num_neighborhoods
            zone_facilities[nh_zones[zone_idx].name].append(f)

    zone_facilities[ZONE_UTILITY] = utility_facilities

    # Pack within zones
    occupied: set[tuple[int, int]] = set()
    all_placed: list[Placement] = []
    all_overflow: list[Facility] = []

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


def compute_arrangement(
    state: GameState,
) -> tuple[list[Placement], list[Facility]]:
    """Compute new positions for all facilities without mutating state.

    Small farms (tiers 1-2) use a 3-zone type-grouped layout.
    Large farms (tiers 3+) use self-contained neighborhoods where each
    neighborhood has one of each essential facility type.

    Returns (placements, overflow) where overflow facilities couldn't fit.
    """
    facilities = state.get_facilities_list()
    if not facilities:
        return [], []

    farm = state.farm

    if _is_small_farm(farm):
        return _compute_small_farm_arrangement(facilities, farm)
    else:
        return _compute_neighborhood_arrangement(facilities, farm)


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
