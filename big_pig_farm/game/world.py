"""Farm grid and spatial management with A* pathfinding."""

import random
from enum import Enum
from typing import Optional
from uuid import UUID
import heapq

from pydantic import BaseModel, Field

from big_pig_farm.data.config import FARM_TIERS, SIMULATION
from big_pig_farm.entities.facilities import Facility, FacilityType


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


class FarmGrid(BaseModel):
    """The farm world grid with pathfinding support."""
    width: int
    height: int
    tier: int = 1
    cells: list[list[Cell]] = Field(default_factory=list)

    # Cached list of walkable interior positions (invalidated on grid changes)
    _walkable_cache: Optional[list[tuple[int, int]]] = None

    model_config = {"arbitrary_types_allowed": True}

    def model_post_init(self, __context) -> None:
        """Initialize grid cells after model creation."""
        if not self.cells:
            self.cells = [
                [Cell() for _ in range(self.width)]
                for _ in range(self.height)
            ]
            self._add_border_walls()
        self._walkable_cache = None

    def _invalidate_walkable_cache(self) -> None:
        """Invalidate the cached list of walkable positions."""
        self._walkable_cache = None

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
        """Create a starter farm grid."""
        tier = FARM_TIERS[0]
        return cls(width=tier.width, height=tier.height, tier=1)

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

        # Add new border walls
        self._add_border_walls()

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

        # Add new border walls
        self._add_border_walls()

        return True, offset_x, offset_y

    @property
    def capacity(self) -> int:
        """Get the pig capacity for current tier."""
        if self.tier <= len(FARM_TIERS):
            return FARM_TIERS[self.tier - 1].capacity
        return FARM_TIERS[-1].capacity

    @property
    def next_tier(self) -> Optional["FarmTier"]:
        """Get the next tier info, or None if at max."""
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
        max_iterations = SIMULATION.MAX_PATHFINDING_ITERATIONS

        while open_set and iterations < max_iterations:
            iterations += 1
            _, current = heapq.heappop(open_set)

            if current == goal:
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

        return []  # No path found

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
