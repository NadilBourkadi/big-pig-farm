"""Farm grid and spatial management with A* pathfinding."""

import random
from enum import Enum
from typing import Optional
from uuid import UUID
import heapq

from pydantic import BaseModel, Field

from big_pig_farm.data.config import FARM_TIERS, ROOM_TIERS, SIMULATION
from big_pig_farm.entities.areas import FarmArea, TunnelConnection
from big_pig_farm.entities.biomes import BiomeType
from big_pig_farm.entities.facilities import Facility, FacilityType


# Tunnel dimensions: 5 cells wide (half-width 2 → range -2..+2)
TUNNEL_HALF_WIDTH = 2


class CellType(str, Enum):
    """Type of terrain in a cell."""
    FLOOR = "floor"
    BEDDING = "bedding"
    GRASS = "grass"
    WALL = "wall"


class Cell(BaseModel):
    """A single cell in the farm grid."""
    cell_type: CellType = CellType.FLOOR
    facility_id: Optional[UUID] = None
    is_walkable: bool = True
    area_id: Optional[UUID] = None  # Which FarmArea this cell belongs to
    is_tunnel: bool = False  # True for tunnel corridor cells
    # Pre-computed wall flags (set by FarmGrid._compute_wall_flags)
    is_corner: bool = False
    is_horizontal_wall: bool = False


class FarmGrid(BaseModel):
    """The farm world grid with pathfinding support."""
    width: int
    height: int
    tier: int = 1
    cells: list[list[Cell]] = Field(default_factory=list)

    # Multi-area support
    areas: list[FarmArea] = Field(default_factory=list)
    tunnels: list[TunnelConnection] = Field(default_factory=list)

    # Cached list of walkable interior positions (invalidated on grid changes)
    _walkable_cache: Optional[list[tuple[int, int]]] = None
    # Per-area walkable position cache (invalidated alongside _walkable_cache)
    _area_walkable_cache: dict[UUID, list[tuple[int, int]]] = {}
    # O(1) area lookup by UUID
    _area_lookup: dict[UUID, FarmArea] = {}

    # Performance counters (reset each debug snapshot window)
    _pathfind_calls: int = 0
    _pathfind_nodes: int = 0

    model_config = {"arbitrary_types_allowed": True}

    def model_post_init(self, __context) -> None:
        """Initialize grid cells after model creation."""
        if not self.cells:
            self.cells = [
                [Cell() for _ in range(self.width)]
                for _ in range(self.height)
            ]
        self._walkable_cache = None
        self._area_walkable_cache = {}
        self._area_lookup = {a.id: a for a in self.areas}

    def _invalidate_walkable_cache(self) -> None:
        """Invalidate the cached list of walkable positions."""
        self._walkable_cache = None
        self._area_walkable_cache = {}

    def _compute_wall_flags(self) -> None:
        """Pre-compute is_corner and is_horizontal_wall for all wall cells.

        This replaces the per-area iteration in rendering that previously
        looped over all areas for every wall cell every frame.
        """
        # Reset all flags first
        for row in self.cells:
            for cell in row:
                cell.is_corner = False
                cell.is_horizontal_wall = False

        for area in self.areas:
            for x in range(area.x1, area.x2 + 1):
                for y in range(area.y1, area.y2 + 1):
                    if not self.is_valid_position(x, y):
                        continue
                    cell = self.cells[y][x]
                    if cell.cell_type != CellType.WALL:
                        continue
                    if x in (area.x1, area.x2) and y in (area.y1, area.y2):
                        cell.is_corner = True
                    elif y in (area.y1, area.y2) and area.x1 <= x <= area.x2:
                        cell.is_horizontal_wall = True

    def _add_border_walls(self) -> None:
        """Add walls around the farm perimeter."""
        for x in range(self.width):
            self.cells[0][x].cell_type = CellType.WALL
            self.cells[0][x].is_walkable = False
            self.cells[self.height - 1][x].cell_type = CellType.WALL
            self.cells[self.height - 1][x].is_walkable = False

        for y in range(self.height):
            self.cells[y][0].cell_type = CellType.WALL
            self.cells[y][0].is_walkable = False
            self.cells[y][self.width - 1].cell_type = CellType.WALL
            self.cells[y][self.width - 1].is_walkable = False

        self._invalidate_walkable_cache()

    @classmethod
    def create_starter(cls) -> "FarmGrid":
        """Create a starter farm grid with a MEADOW area."""
        room = ROOM_TIERS[0]
        grid = cls(width=room.room_width, height=room.room_height, tier=1)
        grid._create_legacy_starter_area()
        return grid

    def _create_legacy_starter_area(self) -> None:
        """Create a MEADOW starter area covering the entire grid.

        Used by create_starter() and as a safety net for legacy saves where
        area data is missing.
        """
        area = FarmArea(
            name="Meadow Room",
            biome=BiomeType.MEADOW,
            x1=0, y1=0,
            x2=self.width - 1, y2=self.height - 1,
            is_starter=True,
        )
        self.add_area(area)

    def upgrade_to_tier(self, new_tier: int) -> bool:
        """Upgrade the farm to a new tier, expanding the grid."""
        if new_tier <= self.tier or new_tier > len(FARM_TIERS):
            return False

        tier_info = FARM_TIERS[new_tier - 1]
        old_width = self.width
        old_height = self.height

        # Create new larger grid
        new_cells = [
            [Cell() for _ in range(tier_info.width)]
            for _ in range(tier_info.height)
        ]

        # Copy old cells to new grid (centered)
        offset_x = (tier_info.width - old_width) // 2
        offset_y = (tier_info.height - old_height) // 2

        for y in range(old_height):
            for x in range(old_width):
                old_cell = self.cells[y][x]
                # Skip old walls, we'll add new ones
                if old_cell.cell_type != CellType.WALL:
                    new_cells[y + offset_y][x + offset_x] = old_cell

        # Update grid
        self.width = tier_info.width
        self.height = tier_info.height
        self.tier = new_tier
        self.cells = new_cells

        return True

    def resize_to_match_config(self) -> tuple[bool, int, int]:
        """Resize farm to match current config for its tier.

        Returns (resized, offset_x, offset_y) - offsets for repositioning entities.
        """
        if self.tier < 1 or self.tier > len(FARM_TIERS):
            return False, 0, 0

        tier_info = FARM_TIERS[self.tier - 1]

        # Check if already correct size
        if self.width == tier_info.width and self.height == tier_info.height:
            return False, 0, 0

        old_width = self.width
        old_height = self.height

        # Create new grid with config dimensions
        new_cells = [
            [Cell() for _ in range(tier_info.width)]
            for _ in range(tier_info.height)
        ]

        # Calculate offset to center old content in new grid
        offset_x = (tier_info.width - old_width) // 2
        offset_y = (tier_info.height - old_height) // 2

        # Copy old cells to new grid (centered)
        for y in range(old_height):
            for x in range(old_width):
                new_x = x + offset_x
                new_y = y + offset_y
                # Bounds check for the new grid
                if 0 <= new_x < tier_info.width and 0 <= new_y < tier_info.height:
                    old_cell = self.cells[y][x]
                    # Skip old walls, we'll add new ones
                    if old_cell.cell_type != CellType.WALL:
                        new_cells[new_y][new_x] = old_cell

        # Update grid
        self.width = tier_info.width
        self.height = tier_info.height
        self.cells = new_cells

        return True, offset_x, offset_y

    @property
    def capacity(self) -> int:
        """Get the pig capacity — sum of all room capacities.

        Also considers the tier field for backward compatibility: when the
        tier was set directly (e.g. in tests or legacy saves), use the
        higher of area-based and tier-based capacity.
        """
        # Area-based capacity
        area_cap = 0
        for i, _area in enumerate(self.areas):
            tier_idx = min(i, len(ROOM_TIERS) - 1)
            area_cap += ROOM_TIERS[tier_idx].capacity_add

        # Tier-based capacity (legacy)
        tier_cap = 0
        if self.tier <= len(FARM_TIERS):
            tier_cap = FARM_TIERS[self.tier - 1].capacity
        else:
            tier_cap = FARM_TIERS[-1].capacity

        return max(area_cap, tier_cap)

    @property
    def next_room_tier(self) -> Optional["RoomTier"]:
        """Get the tier info for the next room addition, or None if at max."""
        next_idx = len(self.areas)
        if next_idx < len(ROOM_TIERS):
            return ROOM_TIERS[next_idx]
        return None

    @property
    def next_tier(self) -> Optional["FarmTier"]:
        """Get the next tier info, or None if at max (legacy compat)."""
        if self.tier < len(FARM_TIERS):
            return FARM_TIERS[self.tier]
        return None

    def is_valid_position(self, x: int, y: int) -> bool:
        """Check if a position is within bounds."""
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        """Check if a position can be walked on."""
        if not self.is_valid_position(x, y):
            return False
        return self.cells[y][x].is_walkable

    def get_cell(self, x: int, y: int) -> Optional[Cell]:
        """Get cell at position, or None if out of bounds."""
        if not self.is_valid_position(x, y):
            return None
        return self.cells[y][x]

    def place_facility(self, facility: Facility) -> bool:
        """Place a facility on the grid. Returns True if successful."""
        # Check all cells are available
        for cell_x, cell_y in facility.cells:
            if not self.is_valid_position(cell_x, cell_y):
                return False
            cell = self.cells[cell_y][cell_x]
            if cell.facility_id is not None or not cell.is_walkable:
                return False

        # Place the facility
        for cell_x, cell_y in facility.cells:
            self.cells[cell_y][cell_x].facility_id = facility.id
            self.cells[cell_y][cell_x].is_walkable = False

        # Keep interaction point walkable
        ix, iy = facility.interaction_point
        if self.is_valid_position(ix, iy):
            # Interaction point is adjacent, should remain walkable
            pass

        self._invalidate_walkable_cache()
        return True

    def remove_facility(self, facility: Facility) -> None:
        """Remove a facility from the grid."""
        for cell_x, cell_y in facility.cells:
            if self.is_valid_position(cell_x, cell_y):
                self.cells[cell_y][cell_x].facility_id = None
                self.cells[cell_y][cell_x].is_walkable = True
        self._invalidate_walkable_cache()

    def get_neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        """Get walkable neighboring cells (4-directional)."""
        neighbors = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if self.is_walkable(nx, ny):
                neighbors.append((nx, ny))
        return neighbors

    def find_path(
        self,
        start: tuple[int, int],
        goal: tuple[int, int],
    ) -> list[tuple[int, int]]:
        """Find path from start to goal using A* algorithm."""
        self._pathfind_calls += 1

        if not self.is_walkable(goal[0], goal[1]):
            # Try to find nearest walkable cell to goal
            goal = self._find_nearest_walkable(goal)
            if goal is None:
                return []

        if start == goal:
            return [start]

        # A* algorithm
        open_set: list[tuple[float, tuple[int, int]]] = [(0, start)]
        came_from: dict[tuple[int, int], tuple[int, int]] = {}
        g_score: dict[tuple[int, int], float] = {start: 0}
        f_score: dict[tuple[int, int], float] = {start: self._heuristic(start, goal)}

        iterations = 0
        max_iterations = SIMULATION.MAX_PATHFINDING_ITERATIONS + 500 * len(self.areas)

        while open_set and iterations < max_iterations:
            iterations += 1
            _, current = heapq.heappop(open_set)

            if current == goal:
                self._pathfind_nodes += iterations
                # Reconstruct path
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                return path

            for neighbor in self.get_neighbors(current[0], current[1]):
                tentative_g = g_score[current] + 1  # Cost is 1 per cell

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f = tentative_g + self._heuristic(neighbor, goal)
                    f_score[neighbor] = f
                    heapq.heappush(open_set, (f, neighbor))

        self._pathfind_nodes += iterations
        return []  # No path found

    def reset_perf_counters(self) -> None:
        """Reset pathfinding performance counters for the next snapshot window."""
        self._pathfind_calls = 0
        self._pathfind_nodes = 0

    def _heuristic(self, a: tuple[int, int], b: tuple[int, int]) -> float:
        """Manhattan distance heuristic for A*."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _find_nearest_walkable(
        self,
        pos: tuple[int, int],
        max_distance: int = 5,
    ) -> Optional[tuple[int, int]]:
        """Find the nearest walkable cell to a position."""
        x, y = pos
        for distance in range(1, max_distance + 1):
            for dx in range(-distance, distance + 1):
                for dy in range(-distance, distance + 1):
                    if abs(dx) + abs(dy) == distance:
                        nx, ny = x + dx, y + dy
                        if self.is_walkable(nx, ny):
                            return (nx, ny)
        return None

    def find_random_walkable(self) -> Optional[tuple[int, int]]:
        """Find a random walkable position on the grid."""
        if self._walkable_cache is None:
            self._walkable_cache = [
                (x, y)
                for y in range(1, self.height - 1)
                for x in range(1, self.width - 1)
                if self.is_walkable(x, y)
            ]

        if self._walkable_cache:
            return random.choice(self._walkable_cache)
        return None

    def find_random_walkable_in_area(self, area_id: UUID) -> Optional[tuple[int, int]]:
        """Find a random walkable position within a specific area."""
        cached = self._area_walkable_cache.get(area_id)
        if cached is None:
            area = self._area_lookup.get(area_id)
            if area is None:
                return None
            cached = [
                (x, y)
                for y in range(area.y1, area.y2 + 1)
                for x in range(area.x1, area.x2 + 1)
                if self.is_walkable(x, y) and self.cells[y][x].area_id == area_id
            ]
            self._area_walkable_cache[area_id] = cached
        if cached:
            return random.choice(cached)
        return None

    def get_area_at(self, x: int, y: int) -> Optional[FarmArea]:
        """Get the area that a position belongs to."""
        if not self.is_valid_position(x, y):
            return None
        aid = self.cells[y][x].area_id
        if aid is None:
            return None
        return self._area_lookup.get(aid)

    def get_area_by_id(self, area_id: UUID) -> Optional[FarmArea]:
        """Get an area by its UUID."""
        return self._area_lookup.get(area_id)

    def get_biome_at(self, x: int, y: int) -> Optional[BiomeType]:
        """Get the biome type at a position."""
        area = self.get_area_at(x, y)
        if area:
            return area.biome
        return None

    def _repair_area_cells(self) -> None:
        """Re-stamp area_id on border cells and mark void cells non-walkable.

        Needed for saves created before add_area() was used consistently.
        Also marks cells outside any area/tunnel as non-walkable so pigs
        can't wander into the void between areas.
        """
        for area in self.areas:
            for x in range(area.x1, area.x2 + 1):
                for y in range(area.y1, area.y2 + 1):
                    if not self.is_valid_position(x, y):
                        continue
                    cell = self.cells[y][x]
                    if cell.is_tunnel:
                        continue
                    is_border = (x == area.x1 or x == area.x2
                                 or y == area.y1 or y == area.y2)
                    if is_border:
                        cell.cell_type = CellType.WALL
                        cell.is_walkable = False
                        cell.area_id = area.id
                    elif cell.area_id is None:
                        cell.cell_type = CellType.FLOOR
                        cell.is_walkable = True
                        cell.area_id = area.id

        # Mark void cells (outside all areas and tunnels) as non-walkable
        for y in range(self.height):
            for x in range(self.width):
                cell = self.cells[y][x]
                if cell.area_id is None and not cell.is_tunnel:
                    cell.is_walkable = False

        self._compute_wall_flags()
        self._invalidate_walkable_cache()

    def _rebuild_tunnels(self) -> None:
        """Re-carve all tunnel connections using current tunnel dimensions.

        Clears old tunnel cells and re-carves using the current width/count
        settings so existing saves pick up tunnel improvements.
        """
        if len(self.areas) < 2 or not self.tunnels:
            return

        # Collect unique area pairs from existing tunnels
        pairs: list[tuple[FarmArea, FarmArea]] = []
        seen: set[tuple[str, str]] = set()
        for tunnel in self.tunnels:
            key = tuple(sorted((str(tunnel.area_a_id), str(tunnel.area_b_id))))
            if key in seen:
                continue
            seen.add(key)
            area_a = self.get_area_by_id(tunnel.area_a_id)
            area_b = self.get_area_by_id(tunnel.area_b_id)
            if area_a and area_b:
                pairs.append((area_a, area_b))

        # Clear all existing tunnel cells back to their base state
        for tunnel in self.tunnels:
            for x, y in tunnel.cells:
                if self.is_valid_position(x, y):
                    cell = self.cells[y][x]
                    cell.is_tunnel = False
                    # Restore to wall if on an area border, otherwise void
                    if cell.area_id is not None:
                        cell.cell_type = CellType.WALL
                        cell.is_walkable = False
                    else:
                        cell.cell_type = CellType.FLOOR
                        cell.is_walkable = False
        self.tunnels.clear()

        # Re-carve each connection with current settings
        for area_a, area_b in pairs:
            self.connect_areas(area_a, area_b)

    def add_area(self, area: FarmArea) -> None:
        """Register an area and carve its walls and interior cells."""
        self.areas.append(area)
        self._area_lookup[area.id] = area
        # Set wall cells around area perimeter
        for x in range(area.x1, area.x2 + 1):
            for y in range(area.y1, area.y2 + 1):
                if not self.is_valid_position(x, y):
                    continue
                cell = self.cells[y][x]
                is_border = (x == area.x1 or x == area.x2
                             or y == area.y1 or y == area.y2)
                if is_border:
                    cell.cell_type = CellType.WALL
                    cell.is_walkable = False
                    cell.area_id = area.id
                else:
                    cell.cell_type = CellType.FLOOR
                    cell.is_walkable = True
                    cell.area_id = area.id
        self._compute_wall_flags()
        self._invalidate_walkable_cache()

    def connect_areas(self, area_a: FarmArea, area_b: FarmArea) -> list[TunnelConnection]:
        """Carve two 5-wide tunnel corridors between two areas.

        Tunnels are placed at 1/3 and 2/3 of the shared wall overlap so
        traffic can flow through both without bottlenecking.
        """
        dx = area_b.center_x - area_a.center_x
        dy = area_b.center_y - area_a.center_y

        if abs(dx) >= abs(dy):
            return self._carve_horizontal_tunnels(area_a, area_b)
        else:
            return self._carve_vertical_tunnels(area_a, area_b)

    def _carve_one_horizontal_tunnel(
        self, area_a_id, area_b_id, t_x1: int, t_x2: int, center_y: int,
    ) -> TunnelConnection:
        """Carve a single horizontal 5-wide tunnel at the given center_y."""
        hw = TUNNEL_HALF_WIDTH
        tunnel_cells = []

        for x in range(t_x1, t_x2 + 1):
            for dy in range(-hw, hw + 1):
                y = center_y + dy
                if self.is_valid_position(x, y):
                    cell = self.cells[y][x]
                    cell.cell_type = CellType.FLOOR
                    cell.is_walkable = True
                    cell.is_tunnel = True
                    tunnel_cells.append((x, y))

        tunnel = TunnelConnection(
            area_a_id=area_a_id, area_b_id=area_b_id,
            cells=tunnel_cells, orientation="horizontal",
        )
        self.tunnels.append(tunnel)
        return tunnel

    def _carve_horizontal_tunnels(
        self, area_a: FarmArea, area_b: FarmArea,
    ) -> list[TunnelConnection]:
        """Carve two horizontal 5-wide tunnels between two areas."""
        if area_a.center_x > area_b.center_x:
            area_a, area_b = area_b, area_a

        t_x1 = area_a.x2
        t_x2 = area_b.x1

        overlap_y1 = max(area_a.interior_y1, area_b.interior_y1)
        overlap_y2 = min(area_a.interior_y2, area_b.interior_y2)

        if overlap_y2 - overlap_y1 < 2:
            mid_y = (area_a.center_y + area_b.center_y) // 2
            overlap_y1 = mid_y - 1
            overlap_y2 = mid_y + 1

        span = overlap_y2 - overlap_y1
        center_a = overlap_y1 + span // 4
        center_b = overlap_y1 + 3 * span // 4

        tunnels = [
            self._carve_one_horizontal_tunnel(area_a.id, area_b.id, t_x1, t_x2, center_a),
            self._carve_one_horizontal_tunnel(area_a.id, area_b.id, t_x1, t_x2, center_b),
        ]
        self._compute_wall_flags()
        self._invalidate_walkable_cache()
        return tunnels

    def _carve_one_vertical_tunnel(
        self, area_a_id, area_b_id, t_y1: int, t_y2: int, center_x: int,
    ) -> TunnelConnection:
        """Carve a single vertical 5-wide tunnel at the given center_x."""
        hw = TUNNEL_HALF_WIDTH
        tunnel_cells = []

        for y in range(t_y1, t_y2 + 1):
            for dx in range(-hw, hw + 1):
                x = center_x + dx
                if self.is_valid_position(x, y):
                    cell = self.cells[y][x]
                    cell.cell_type = CellType.FLOOR
                    cell.is_walkable = True
                    cell.is_tunnel = True
                    tunnel_cells.append((x, y))

        tunnel = TunnelConnection(
            area_a_id=area_a_id, area_b_id=area_b_id,
            cells=tunnel_cells, orientation="vertical",
        )
        self.tunnels.append(tunnel)
        return tunnel

    def _carve_vertical_tunnels(
        self, area_a: FarmArea, area_b: FarmArea,
    ) -> list[TunnelConnection]:
        """Carve two vertical 5-wide tunnels between two areas."""
        if area_a.center_y > area_b.center_y:
            area_a, area_b = area_b, area_a

        t_y1 = area_a.y2
        t_y2 = area_b.y1

        overlap_x1 = max(area_a.interior_x1, area_b.interior_x1)
        overlap_x2 = min(area_a.interior_x2, area_b.interior_x2)

        if overlap_x2 - overlap_x1 < 2:
            mid_x = (area_a.center_x + area_b.center_x) // 2
            overlap_x1 = mid_x - 1
            overlap_x2 = mid_x + 1

        span = overlap_x2 - overlap_x1
        center_a = overlap_x1 + span // 4
        center_b = overlap_x1 + 3 * span // 4

        tunnels = [
            self._carve_one_vertical_tunnel(area_a.id, area_b.id, t_y1, t_y2, center_a),
            self._carve_one_vertical_tunnel(area_a.id, area_b.id, t_y1, t_y2, center_b),
        ]
        self._compute_wall_flags()
        self._invalidate_walkable_cache()
        return tunnels

    def expand_grid(
        self,
        new_width: int,
        new_height: int,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> None:
        """Expand the grid canvas and shift existing content by offset.

        Creates a larger grid, copies existing cells into it at the offset
        position, and updates all area/tunnel coordinates.  New cells are
        non-walkable void so pigs can't wander into the gap between areas.
        """
        new_cells = [
            [Cell(is_walkable=False) for _ in range(new_width)]
            for _ in range(new_height)
        ]

        # Copy existing cells
        for y in range(self.height):
            for x in range(self.width):
                new_x = x + offset_x
                new_y = y + offset_y
                if 0 <= new_x < new_width and 0 <= new_y < new_height:
                    new_cells[new_y][new_x] = self.cells[y][x]

        self.width = new_width
        self.height = new_height
        self.cells = new_cells

        # Shift area coordinates
        if offset_x != 0 or offset_y != 0:
            for area in self.areas:
                area.x1 += offset_x
                area.y1 += offset_y
                area.x2 += offset_x
                area.y2 += offset_y

            # Shift tunnel cell coordinates
            for tunnel in self.tunnels:
                tunnel.cells = [
                    (x + offset_x, y + offset_y) for x, y in tunnel.cells
                ]

        self._invalidate_walkable_cache()

    def add_room(
        self,
        biome: BiomeType,
        room_name: Optional[str] = None,
    ) -> Optional[tuple[FarmArea, list[TunnelConnection], int, int]]:
        """Add a new room with the given biome, connected to the most recent area.

        Returns (new_area, tunnels, offset_x, offset_y) or None if at max rooms.
        offset_x/offset_y are the grid expansion offsets that entities need
        to be shifted by.
        """
        # Ensure there's at least a starter area to attach to
        if not self.areas:
            self._create_legacy_starter_area()

        room_idx = len(self.areas)
        if room_idx >= len(ROOM_TIERS):
            return None

        room_tier = ROOM_TIERS[room_idx]
        rw = room_tier.room_width
        rh = room_tier.room_height

        if room_name is None:
            from big_pig_farm.entities.biomes import BIOMES
            room_name = f"{BIOMES[biome].display_name} Room"

        # Attach to the most recently added area
        attach_area = self.areas[-1]

        # Try placement directions: RIGHT, BELOW, LEFT, ABOVE
        gap = 4  # Gap between room walls for tunnel corridor
        candidates = [
            # (new_x1, new_y1, direction)
            (attach_area.x2 + gap, attach_area.center_y - rh // 2, "right"),
            (attach_area.center_x - rw // 2, attach_area.y2 + gap, "below"),
            (attach_area.x1 - gap - rw, attach_area.center_y - rh // 2, "left"),
            (attach_area.center_x - rw // 2, attach_area.y1 - gap - rh, "above"),
        ]

        for new_x1, new_y1, _direction in candidates:
            new_x2 = new_x1 + rw - 1
            new_y2 = new_y1 + rh - 1

            # Calculate required grid expansion
            need_left = max(0, -new_x1)
            need_top = max(0, -new_y1)
            need_right = max(0, new_x2 + 1 - self.width)
            need_bottom = max(0, new_y2 + 1 - self.height)

            offset_x = need_left
            offset_y = need_top
            new_grid_w = self.width + need_left + need_right
            new_grid_h = self.height + need_top + need_bottom

            # Expand if needed
            if new_grid_w > self.width or new_grid_h > self.height:
                self.expand_grid(new_grid_w, new_grid_h, offset_x, offset_y)

            # Recalculate position after expansion
            actual_x1 = new_x1 + offset_x
            actual_y1 = new_y1 + offset_y

            # Check the area doesn't overlap existing areas
            actual_x2 = actual_x1 + rw - 1
            actual_y2 = actual_y1 + rh - 1
            overlap = False
            for existing in self.areas:
                if (actual_x1 <= existing.x2 and actual_x2 >= existing.x1
                        and actual_y1 <= existing.y2 and actual_y2 >= existing.y1):
                    overlap = True
                    break
            if overlap:
                continue

            # Create the area
            new_area = FarmArea(
                name=room_name,
                biome=biome,
                x1=actual_x1,
                y1=actual_y1,
                x2=actual_x2,
                y2=actual_y2,
            )
            self.add_area(new_area)

            # Update tier (highest room index + 1)
            self.tier = max(self.tier, room_tier.tier)

            # Connect with tunnels
            tunnels = self.connect_areas(attach_area, new_area)

            return new_area, tunnels, offset_x, offset_y

        return None
