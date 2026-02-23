"""Farm grid and spatial management with A* pathfinding."""

import heapq
import random
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from big_pig_farm.game.state import GameState

from pydantic import BaseModel, Field

from big_pig_farm.data.config import FARM_TIERS, ROOM_TIERS, SIMULATION, FarmTier, RoomTier
from big_pig_farm.entities.areas import FarmArea, TunnelConnection
from big_pig_farm.entities.biomes import BiomeType
from big_pig_farm.entities.facilities import Facility

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
    facility_id: UUID | None = None
    is_walkable: bool = True
    area_id: UUID | None = None  # Which FarmArea this cell belongs to
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
    _walkable_cache: list[tuple[int, int]] | None = None
    # Per-area walkable position cache (invalidated alongside _walkable_cache)
    _area_walkable_cache: dict[UUID, list[tuple[int, int]]] = {}
    # O(1) area lookup by UUID
    _area_lookup: dict[UUID, FarmArea] = {}
    # Biome → areas cache (invalidated on area add/remove)
    _biome_area_cache: dict[str, list[FarmArea]] = {}

    # Grid generation counter — incremented whenever the walkable grid changes
    # (facility placed/removed, area added, tunnels carved).  Used by the
    # cross-tick path cache to invalidate stale entries.
    grid_generation: int = 0

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
        self._biome_area_cache = {}

    def _invalidate_walkable_cache(self) -> None:
        """Invalidate the cached list of walkable positions."""
        self._walkable_cache = None
        self._area_walkable_cache = {}
        self._biome_area_cache = {}
        self.grid_generation += 1

    def _compute_wall_flags(self) -> None:
        """Pre-compute is_corner and is_horizontal_wall for all wall cells.

        This replaces the per-area iteration in rendering that previously
        looped over all areas for every wall cell every frame.
        Tunnel cells with manually-set flags are preserved (barrier walls).
        """
        # Reset flags on non-tunnel cells only (tunnel barrier walls keep theirs)
        for row in self.cells:
            for cell in row:
                if not cell.is_tunnel:
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
        grid.create_legacy_starter_area()
        return grid

    def create_legacy_starter_area(self) -> None:
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
        """Get the pig capacity — sum of all room capacities."""
        total = 0
        for i, _area in enumerate(self.areas):
            tier_idx = min(i, len(ROOM_TIERS) - 1)
            total += ROOM_TIERS[tier_idx].capacity_add
        return total

    @property
    def next_room_tier(self) -> RoomTier | None:
        """Get the tier info for the next room addition, or None if at max."""
        next_idx = len(self.areas)
        if next_idx < len(ROOM_TIERS):
            return ROOM_TIERS[next_idx]
        return None

    @property
    def next_tier(self) -> FarmTier | None:
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

    def get_cell(self, x: int, y: int) -> Cell | None:
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
            goal = self.find_nearest_walkable(goal)
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
        max_iterations = SIMULATION.MAX_PATHFINDING_ITERATIONS + 250 * len(self.areas)

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

    def find_nearest_walkable(
        self,
        pos: tuple[int, int],
        max_distance: int = 5,
    ) -> tuple[int, int] | None:
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

    def find_random_walkable(self) -> tuple[int, int] | None:
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

    def find_random_walkable_in_area(self, area_id: UUID) -> tuple[int, int] | None:
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

    def get_area_at(self, x: int, y: int) -> FarmArea | None:
        """Get the area that a position belongs to."""
        if not self.is_valid_position(x, y):
            return None
        aid = self.cells[y][x].area_id
        if aid is None:
            return None
        return self._area_lookup.get(aid)

    def get_area_by_id(self, area_id: UUID) -> FarmArea | None:
        """Get an area by its UUID."""
        return self._area_lookup.get(area_id)

    def find_areas_by_biome(self, biome_value: str) -> list[FarmArea]:
        """Return all areas with the given biome string value (cached)."""
        if not self._biome_area_cache:
            for area in self.areas:
                self._biome_area_cache.setdefault(area.biome.value, []).append(area)
        return self._biome_area_cache.get(biome_value, [])

    def get_area_capacity(self, area_id: UUID) -> int:
        """Get the pig capacity for an area based on its position in the room list."""
        for i, area in enumerate(self.areas):
            if area.id == area_id:
                tier_idx = min(i, len(ROOM_TIERS) - 1)
                return ROOM_TIERS[tier_idx].capacity_add
        return 0

    def get_biome_at(self, x: int, y: int) -> BiomeType | None:
        """Get the biome type at a position."""
        area = self.get_area_at(x, y)
        if area:
            return area.biome
        return None

    def repair_area_cells(self) -> None:
        """Re-stamp area_id on border cells and mark void cells non-walkable.

        Needed for saves created before add_area() was used consistently.
        Also cleans up ghost cells — cells whose area_id points to an area
        that no longer contains that position (from room repositioning).
        """
        # First pass: clear orphaned area_id from cells outside their area
        for y in range(self.height):
            for x in range(self.width):
                cell = self.cells[y][x]
                if cell.area_id is None or cell.is_tunnel:
                    continue
                area = self.get_area_by_id(cell.area_id)
                if area is None or not area.contains(x, y):
                    cell.area_id = None
                    cell.facility_id = None
                    cell.cell_type = CellType.FLOOR
                    cell.is_walkable = False
                    cell.is_corner = False
                    cell.is_horizontal_wall = False

        # Second pass: stamp cells within each area's bounds
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
                    else:
                        # Unconditionally reset interior cells — fixes stale
                        # WALL cells left behind when rooms reposition.
                        cell.cell_type = CellType.FLOOR
                        if cell.facility_id is None:
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

    def _get_adjacent_pairs(self) -> list[tuple[FarmArea, FarmArea]]:
        """Return all pairs of rooms in horizontally/vertically adjacent grid slots."""
        pairs: list[tuple[FarmArea, FarmArea]] = []
        by_slot: dict[tuple[int, int], FarmArea] = {}
        for area in self.areas:
            by_slot[(area.grid_col, area.grid_row)] = area

        for (col, row), area in by_slot.items():
            # Right neighbor
            right = by_slot.get((col + 1, row))
            if right is not None:
                pairs.append((area, right))
            # Below neighbor
            below = by_slot.get((col, row + 1))
            if below is not None:
                pairs.append((area, below))

        return pairs

    def rebuild_tunnels(self) -> None:
        """Re-carve all tunnel connections using current tunnel dimensions.

        Uses _get_adjacent_pairs() so newly adjacent rooms after relayout
        get connected, and connections to non-adjacent rooms are dropped.
        """
        if len(self.areas) < 2:
            return

        # Clear all existing tunnel cells back to their base state
        for tunnel in self.tunnels:
            for x, y in tunnel.cells:
                if self.is_valid_position(x, y):
                    cell = self.cells[y][x]
                    cell.is_tunnel = False
                    cell.is_horizontal_wall = False
                    # Restore to wall if on an area border, otherwise void
                    if cell.area_id is not None:
                        cell.cell_type = CellType.WALL
                        cell.is_walkable = False
                    else:
                        cell.cell_type = CellType.FLOOR
                        cell.is_walkable = False
        self.tunnels.clear()

        # Re-carve each adjacent pair with current settings
        for area_a, area_b in self._get_adjacent_pairs():
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
        """Carve a single horizontal 5-wide tunnel with barrier walls."""
        hw = TUNNEL_HALF_WIDTH
        tunnel_cells = []

        for x in range(t_x1, t_x2 + 1):
            # Walkable corridor
            for dy in range(-hw, hw + 1):
                y = center_y + dy
                if self.is_valid_position(x, y):
                    cell = self.cells[y][x]
                    cell.cell_type = CellType.FLOOR
                    cell.is_walkable = True
                    cell.is_tunnel = True
                    tunnel_cells.append((x, y))

            # Barrier walls on both sides of the corridor
            for barrier_dy in (-(hw + 1), hw + 1):
                y = center_y + barrier_dy
                if self.is_valid_position(x, y):
                    cell = self.cells[y][x]
                    cell.cell_type = CellType.WALL
                    cell.is_walkable = False
                    cell.is_tunnel = True
                    cell.is_horizontal_wall = True
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
        """Carve a single vertical tunnel with barrier walls.

        Uses double the half-width of horizontal tunnels to compensate
        for terminal characters being ~2x taller than wide.
        """
        hw = TUNNEL_HALF_WIDTH * 2 + 1
        tunnel_cells = []

        for y in range(t_y1, t_y2 + 1):
            # Walkable corridor
            for dx in range(-hw, hw + 1):
                x = center_x + dx
                if self.is_valid_position(x, y):
                    cell = self.cells[y][x]
                    cell.cell_type = CellType.FLOOR
                    cell.is_walkable = True
                    cell.is_tunnel = True
                    tunnel_cells.append((x, y))

            # Barrier walls on both sides of the corridor
            for barrier_dx in (-(hw + 1), hw + 1):
                x = center_x + barrier_dx
                if self.is_valid_position(x, y):
                    cell = self.cells[y][x]
                    cell.cell_type = CellType.WALL
                    cell.is_walkable = False
                    cell.is_tunnel = True
                    # Vertical tunnel barrier walls are vertical walls (not horizontal)
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

    def _compute_grid_layout(self) -> dict[int, tuple[int, int]]:
        """Compute world-coordinate origins for each area using 2-column grid.

        Returns {area_index: (x1, y1)} for each area.
        """
        gap = 7  # Gap between room walls for tunnel corridor

        # Collect room dimensions per slot
        slots: list[tuple[int, int, int, int]] = []  # (col, row, width, height)
        for i, area in enumerate(self.areas):
            col = area.grid_col
            row = area.grid_row
            room_w = area.x2 - area.x1 + 1
            room_h = area.y2 - area.y1 + 1
            slots.append((col, row, room_w, room_h))

        # Compute max width per column and max height per row
        max_col = max(s[0] for s in slots) if slots else 0
        max_row = max(s[1] for s in slots) if slots else 0

        col_widths = [0] * (max_col + 1)
        row_heights = [0] * (max_row + 1)
        for col, row, w, h in slots:
            col_widths[col] = max(col_widths[col], w)
            row_heights[row] = max(row_heights[row], h)

        # Cumulative offsets
        col_offsets = [0] * (max_col + 1)
        for c in range(1, max_col + 1):
            col_offsets[c] = col_offsets[c - 1] + col_widths[c - 1] + gap
        row_offsets = [0] * (max_row + 1)
        for r in range(1, max_row + 1):
            row_offsets[r] = row_offsets[r - 1] + row_heights[r - 1] + gap

        # Compute origin for each area, centered within its slot
        origins: dict[int, tuple[int, int]] = {}
        for i, (col, row, w, h) in enumerate(slots):
            cx = col_offsets[col] + (col_widths[col] - w) // 2
            cy = row_offsets[row] + (row_heights[row] - h) // 2
            origins[i] = (cx, cy)

        return origins

    def add_room(
        self,
        biome: BiomeType,
        room_name: str | None = None,
    ) -> tuple[FarmArea, list[TunnelConnection], int, int, dict[UUID, tuple[int, int]]] | None:
        """Add a new room with the given biome using 2-column grid layout.

        Returns (new_area, tunnels, offset_x, offset_y, room_deltas) or None
        if at max rooms.  offset_x/offset_y are the grid expansion offsets.
        room_deltas maps area_id → (dx, dy) for each existing area that
        repositioned (callers must use this to relocate entities per-room).
        """
        # Ensure there's at least a starter area to attach to
        if not self.areas:
            self.create_legacy_starter_area()

        room_idx = len(self.areas)
        if room_idx >= len(ROOM_TIERS):
            return None

        room_tier = ROOM_TIERS[room_idx]
        rw = room_tier.room_width
        rh = room_tier.room_height

        if room_name is None:
            from big_pig_farm.entities.biomes import BIOMES
            room_name = f"{BIOMES[biome].display_name} Room"

        # Assign next grid slot (reading order, 2 columns)
        new_col = room_idx % 2
        new_row = room_idx // 2

        # Create the area with placeholder coordinates (will be repositioned)
        new_area = FarmArea(
            name=room_name,
            biome=biome,
            x1=0, y1=0,
            x2=rw - 1, y2=rh - 1,
            grid_col=new_col, grid_row=new_row,
        )

        # Temporarily add to areas list to compute full grid layout
        self.areas.append(new_area)
        self._area_lookup[new_area.id] = new_area
        origins = self._compute_grid_layout()

        # Compute required grid size
        total_w = 0
        total_h = 0
        for i, area in enumerate(self.areas):
            ox, oy = origins[i]
            aw = area.x2 - area.x1 + 1
            ah = area.y2 - area.y1 + 1
            total_w = max(total_w, ox + aw)
            total_h = max(total_h, oy + ah)

        # Remove the temporarily added area (we'll re-add via add_area below)
        self.areas.pop()
        del self._area_lookup[new_area.id]

        # Compute offset needed to shift existing content
        # (existing areas already have world coords, new layout may differ)
        offset_x = 0
        offset_y = 0
        if len(self.areas) > 0:
            # Check if existing areas need shifting
            old_origin_0 = (self.areas[0].x1, self.areas[0].y1)
            new_origin_0 = origins[0]
            offset_x = new_origin_0[0] - old_origin_0[0]
            offset_y = new_origin_0[1] - old_origin_0[1]

        # Expand grid if needed
        need_w = max(self.width + max(0, offset_x), total_w)
        need_h = max(self.height + max(0, offset_y), total_h)

        # If there's negative offset (existing content needs to shift right/down)
        shift_x = max(0, -offset_x) if offset_x < 0 else 0
        shift_y = max(0, -offset_y) if offset_y < 0 else 0
        if shift_x > 0 or shift_y > 0:
            need_w = max(need_w, self.width + shift_x)
            need_h = max(need_h, self.height + shift_y)

        # Only shift existing content if offset changed
        entity_offset_x = 0
        entity_offset_y = 0
        room_deltas: dict[UUID, tuple[int, int]] = {}
        if offset_x != 0 or offset_y != 0:
            # We need to rebuild the entire grid with proper positions
            # Clear tunnel cells first
            for tunnel in self.tunnels:
                for x, y in tunnel.cells:
                    if self.is_valid_position(x, y):
                        cell = self.cells[y][x]
                        cell.is_tunnel = False
                        cell.is_horizontal_wall = False
            self.tunnels.clear()

            # Expand and shift
            if need_w > self.width or need_h > self.height or shift_x > 0 or shift_y > 0:
                self.expand_grid(need_w, need_h, shift_x, shift_y)
                entity_offset_x = shift_x
                entity_offset_y = shift_y

            # Clear all area ownership before repositioning so orphaned
            # cells at old positions don't render as ghost walls/floors
            for row in self.cells:
                for cell in row:
                    if cell.area_id is not None and not cell.is_tunnel:
                        cell.area_id = None
                        cell.cell_type = CellType.FLOOR
                        cell.is_walkable = False
                        cell.is_corner = False
                        cell.is_horizontal_wall = False

            # Compute per-room deltas BEFORE repositioning (after grid shift)
            for i, area in enumerate(self.areas):
                target_x1, target_y1 = origins[i]
                dx = target_x1 - area.x1
                dy = target_y1 - area.y1
                if dx != 0 or dy != 0:
                    room_deltas[area.id] = (dx, dy)

            # Reposition existing areas to their new grid positions
            for i, area in enumerate(self.areas):
                target_x1, target_y1 = origins[i]
                aw = area.x2 - area.x1 + 1
                ah = area.y2 - area.y1 + 1
                area.x1 = target_x1
                area.y1 = target_y1
                area.x2 = target_x1 + aw - 1
                area.y2 = target_y1 + ah - 1

            # Rebuild cells for all existing areas
            self.repair_area_cells()
        elif need_w > self.width or need_h > self.height:
            self.expand_grid(need_w, need_h, 0, 0)

        # Place the new area at its computed position
        new_origin = origins[room_idx]
        new_area.x1 = new_origin[0]
        new_area.y1 = new_origin[1]
        new_area.x2 = new_origin[0] + rw - 1
        new_area.y2 = new_origin[1] + rh - 1
        self.add_area(new_area)

        # Rebuild all tunnel connections based on adjacency
        self.rebuild_tunnels()

        return new_area, list(self.tunnels), entity_offset_x, entity_offset_y, room_deltas


def relayout_areas(state: "GameState") -> bool:
    """Migrate a legacy or outdated layout to the 2-column grid layout.

    Assigns grid_col/grid_row to each area, computes new world positions,
    relocates pigs and facilities, and rebuilds the grid fresh.
    Returns True if a relayout was performed, False if already up-to-date.
    """
    farm = state.farm
    if len(farm.areas) < 2:
        return False

    # Step 1: Assign grid slots (idempotent if already set)
    for i, area in enumerate(farm.areas):
        area.grid_col = i % 2
        area.grid_row = i // 2

    # Step 2: Compute expected positions using grid layout
    origins = farm._compute_grid_layout()

    # Check if any area is out of position (covers both legacy linear
    # layouts and gap-size changes)
    needs_relayout = any(
        (area.x1, area.y1) != origins[i]
        for i, area in enumerate(farm.areas)
    )
    if not needs_relayout:
        return False

    # Step 3: Compute deltas and relocate entities
    deltas: dict[UUID, tuple[int, int]] = {}
    for i, area in enumerate(farm.areas):
        target_x1, target_y1 = origins[i]
        dx = target_x1 - area.x1
        dy = target_y1 - area.y1
        deltas[area.id] = (dx, dy)

    # Relocate pigs (those in tunnel corridors will be clamped later)
    for pig in state.get_pigs_list():
        area = farm.get_area_at(int(pig.position.x), int(pig.position.y))
        if area and area.id in deltas:
            dx, dy = deltas[area.id]
            pig.position.x += dx
            pig.position.y += dy
        pig.path = []
        pig.target_position = None
        pig.target_facility_id = None

    # Relocate facilities
    for facility in state.get_facilities_list():
        area = farm.get_area_at(facility.position_x, facility.position_y)
        if area and area.id in deltas:
            dx, dy = deltas[area.id]
            farm.remove_facility(facility)
            facility.position_x += dx
            facility.position_y += dy

    # Step 4: Update area coordinates
    for i, area in enumerate(farm.areas):
        target_x1, target_y1 = origins[i]
        aw = area.x2 - area.x1 + 1
        ah = area.y2 - area.y1 + 1
        area.x1 = target_x1
        area.y1 = target_y1
        area.x2 = target_x1 + aw - 1
        area.y2 = target_y1 + ah - 1

    # Step 5: Compute required grid size and rebuild
    total_w = 0
    total_h = 0
    for area in farm.areas:
        total_w = max(total_w, area.x2 + 1)
        total_h = max(total_h, area.y2 + 1)

    # Rebuild grid fresh
    farm.width = total_w
    farm.height = total_h
    farm.cells = [
        [Cell(is_walkable=False) for _ in range(total_w)]
        for _ in range(total_h)
    ]
    farm.tunnels.clear()

    # Re-carve all areas
    saved_areas = list(farm.areas)
    farm.areas.clear()
    farm._area_lookup.clear()
    for area in saved_areas:
        farm.add_area(area)

    # Re-place facilities
    for facility in state.get_facilities_list():
        farm.place_facility(facility)

    # Rebuild tunnels using adjacency pairs
    farm.rebuild_tunnels()

    # Clamp any orphaned pigs (e.g. those that were in tunnel corridors)
    # to the nearest walkable cell
    for pig in state.get_pigs_list():
        px, py = int(pig.position.x), int(pig.position.y)
        if not farm.is_walkable(px, py):
            walkable = farm.find_nearest_walkable((px, py), max_distance=20)
            if walkable:
                pig.position.x = float(walkable[0])
                pig.position.y = float(walkable[1])

    return True
