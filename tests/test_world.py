"""Tests for the world/grid system."""

import pytest
from big_pig_farm.game.world import FarmGrid, Cell, CellType
from big_pig_farm.entities.facilities import Facility, FacilityType


class TestFarmGrid:
    """Tests for the farm grid."""

    def test_create_starter_farm(self):
        """Test creating a starter farm."""
        farm = FarmGrid.create_starter()

        assert farm.width == 30
        assert farm.height == 15
        assert farm.tier == 1

    def test_grid_bounds(self):
        """Test grid boundary checking."""
        farm = FarmGrid.create_starter()

        assert farm.is_valid_position(5, 5) is True
        assert farm.is_valid_position(-1, 5) is False
        assert farm.is_valid_position(5, -1) is False
        assert farm.is_valid_position(100, 5) is False

    def test_wall_boundaries(self):
        """Test that walls are created around the farm."""
        farm = FarmGrid.create_starter()

        # Walls should not be walkable
        assert farm.is_walkable(0, 0) is False
        assert farm.is_walkable(0, 5) is False
        assert farm.is_walkable(farm.width - 1, 5) is False

        # Interior should be walkable
        assert farm.is_walkable(5, 5) is True

    def test_place_facility(self):
        """Test placing a facility."""
        farm = FarmGrid.create_starter()
        facility = Facility.create(FacilityType.FOOD_BOWL, 5, 5)

        result = farm.place_facility(facility)
        assert result is True

        # Cells should now have facility and not be walkable
        for x, y in facility.cells:
            cell = farm.get_cell(x, y)
            assert cell.facility_id == facility.id
            assert cell.is_walkable is False

    def test_place_facility_collision(self):
        """Test that facilities can't overlap."""
        farm = FarmGrid.create_starter()
        facility1 = Facility.create(FacilityType.FOOD_BOWL, 5, 5)
        facility2 = Facility.create(FacilityType.FOOD_BOWL, 5, 5)

        assert farm.place_facility(facility1) is True
        assert farm.place_facility(facility2) is False

    def test_remove_facility(self):
        """Test removing a facility."""
        farm = FarmGrid.create_starter()
        facility = Facility.create(FacilityType.FOOD_BOWL, 5, 5)

        farm.place_facility(facility)
        farm.remove_facility(facility)

        # Cells should be walkable again
        for x, y in facility.cells:
            cell = farm.get_cell(x, y)
            assert cell.facility_id is None
            assert cell.is_walkable is True


class TestPathfinding:
    """Tests for A* pathfinding."""

    def test_simple_path(self):
        """Test finding a simple path."""
        farm = FarmGrid.create_starter()

        path = farm.find_path((2, 2), (5, 2))
        assert len(path) > 0
        assert path[0] == (2, 2)
        assert path[-1] == (5, 2)

    def test_path_around_obstacle(self):
        """Test pathfinding around an obstacle."""
        farm = FarmGrid.create_starter()

        # Place a facility as obstacle
        facility = Facility.create(FacilityType.HIDEOUT, 4, 2)
        farm.place_facility(facility)

        # Try to path through where facility is
        path = farm.find_path((2, 3), (8, 3))

        # Should find a path (going around)
        assert len(path) > 0
        assert path[0] == (2, 3)
        assert path[-1] == (8, 3)

        # Path should not go through facility cells
        facility_cells = set(facility.cells)
        for point in path:
            assert point not in facility_cells

    def test_no_path_exists(self):
        """Test when no path exists."""
        farm = FarmGrid(width=5, height=5)

        # Block all paths with walls
        for y in range(5):
            farm.cells[y][2].is_walkable = False

        path = farm.find_path((1, 2), (3, 2))
        assert len(path) == 0

    def test_find_random_walkable(self):
        """Test finding a random walkable position."""
        farm = FarmGrid.create_starter()

        pos = farm.find_random_walkable()
        assert pos is not None
        assert farm.is_walkable(pos[0], pos[1])

    def test_get_neighbors(self):
        """Test getting neighboring cells."""
        farm = FarmGrid.create_starter()

        neighbors = farm.get_neighbors(5, 5)
        assert len(neighbors) == 4  # 4 cardinal directions
        assert (5, 4) in neighbors
        assert (5, 6) in neighbors
        assert (4, 5) in neighbors
        assert (6, 5) in neighbors
