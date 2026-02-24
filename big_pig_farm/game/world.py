"""Farm grid and spatial management.

Core cell/grid types live here.  Heavy logic is split across:
- world_pathfinding  (A*, random walkable lookups)
- world_tunnels      (tunnel carving between areas)
- world_areas        (area registration, repair, rebuild)
- world_expansion    (grid expansion, room addition)
- world_migration    (legacy layout migration)
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field

from big_pig_farm.data.config import FARM_TIERS, ROOM_TIERS, FarmTier, RoomTier
from big_pig_farm.entities.areas import FarmArea, TunnelConnection
from big_pig_farm.entities.biomes import BiomeType
from big_pig_farm.entities.facilities import Facility

if TYPE_CHECKING:
    from big_pig_farm.game.state import GameState

# Tunnel dimensions: 5 cells wide (half-width 2 -> range -2..+2)
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
    # Biome -> areas cache (invalidated on area add/remove)
    _biome_area_cache: dict[str, list[FarmArea]] = {}

    # Grid generation counter -- incremented whenever the walkable grid changes
    # (facility placed/removed, area added, tunnels carved).  Used by the
    # cross-tick path cache to invalidate stale entries.
    _grid_generation: int = 0

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
        self._grid_generation += 1

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
    def create_starter(cls) -> FarmGrid:
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
        """Get the pig capacity -- sum of all room capacities."""
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

    # ------------------------------------------------------------------
    # Cell queries
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Facility placement
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Area lookup queries
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Delegating methods -- pathfinding (see world_pathfinding.py)
    # ------------------------------------------------------------------

    def get_neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        """Get walkable neighboring cells (4-directional)."""
        from big_pig_farm.game.world_pathfinding import get_neighbors
        return get_neighbors(self, x, y)

    def find_path(
        self,
        start: tuple[int, int],
        goal: tuple[int, int],
    ) -> list[tuple[int, int]]:
        """Find path from start to goal using A* algorithm."""
        from big_pig_farm.game.world_pathfinding import find_path
        return find_path(self, start, goal)

    def reset_perf_counters(self) -> None:
        """Reset pathfinding performance counters for the next snapshot window."""
        from big_pig_farm.game.world_pathfinding import reset_perf_counters
        reset_perf_counters(self)

    def _heuristic(self, a: tuple[int, int], b: tuple[int, int]) -> float:
        """Manhattan distance heuristic for A*."""
        from big_pig_farm.game.world_pathfinding import heuristic
        return heuristic(a, b)

    def _find_nearest_walkable(
        self,
        pos: tuple[int, int],
        max_distance: int = 5,
    ) -> tuple[int, int] | None:
        """Find the nearest walkable cell to a position."""
        from big_pig_farm.game.world_pathfinding import find_nearest_walkable
        return find_nearest_walkable(self, pos, max_distance)

    def find_random_walkable(self) -> tuple[int, int] | None:
        """Find a random walkable position on the grid."""
        from big_pig_farm.game.world_pathfinding import find_random_walkable
        return find_random_walkable(self)

    def find_random_walkable_in_area(self, area_id: UUID) -> tuple[int, int] | None:
        """Find a random walkable position within a specific area."""
        from big_pig_farm.game.world_pathfinding import find_random_walkable_in_area
        return find_random_walkable_in_area(self, area_id)

    # ------------------------------------------------------------------
    # Delegating methods -- tunnels (see world_tunnels.py)
    # ------------------------------------------------------------------

    def connect_areas(
        self, area_a: FarmArea, area_b: FarmArea,
    ) -> list[TunnelConnection]:
        """Carve two 5-wide tunnel corridors between two areas."""
        from big_pig_farm.game.world_tunnels import connect_areas
        return connect_areas(self, area_a, area_b)

    # ------------------------------------------------------------------
    # Delegating methods -- areas (see world_areas.py)
    # ------------------------------------------------------------------

    def _repair_area_cells(self) -> None:
        """Re-stamp area_id on border cells and mark void cells non-walkable."""
        from big_pig_farm.game.world_areas import repair_area_cells
        repair_area_cells(self)

    def _get_adjacent_pairs(self) -> list[tuple[FarmArea, FarmArea]]:
        """Return all pairs of rooms in horizontally/vertically adjacent grid slots."""
        from big_pig_farm.game.world_areas import get_adjacent_pairs
        return get_adjacent_pairs(self)

    def _rebuild_tunnels(self) -> None:
        """Re-carve all tunnel connections using current tunnel dimensions."""
        from big_pig_farm.game.world_areas import rebuild_tunnels
        rebuild_tunnels(self)

    def add_area(self, area: FarmArea) -> None:
        """Register an area and carve its walls and interior cells."""
        from big_pig_farm.game.world_areas import add_area
        add_area(self, area)

    # ------------------------------------------------------------------
    # Delegating methods -- expansion (see world_expansion.py)
    # ------------------------------------------------------------------

    def expand_grid(
        self,
        new_width: int,
        new_height: int,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> None:
        """Expand the grid canvas and shift existing content by offset."""
        from big_pig_farm.game.world_expansion import expand_grid
        expand_grid(self, new_width, new_height, offset_x, offset_y)

    def _compute_grid_layout(self) -> dict[int, tuple[int, int]]:
        """Compute world-coordinate origins for each area using 2-column grid."""
        from big_pig_farm.game.world_expansion import compute_grid_layout
        return compute_grid_layout(self)

    def add_room(
        self,
        biome: BiomeType,
        room_name: str | None = None,
    ) -> tuple[FarmArea, list[TunnelConnection], int, int, dict[UUID, tuple[int, int]]] | None:
        """Add a new room with the given biome using 2-column grid layout."""
        from big_pig_farm.game.world_expansion import add_room
        return add_room(self, biome, room_name)


def relayout_areas(state: GameState) -> bool:
    """Migrate a legacy or outdated layout to the 2-column grid layout.

    Delegates to world_migration.relayout_areas().
    """
    from big_pig_farm.game.world_migration import relayout_areas as _relayout
    return _relayout(state)
