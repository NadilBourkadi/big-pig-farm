"""Tests for area layout, tunnels, and multi-room pathfinding."""

from big_pig_farm.entities.areas import FarmArea
from big_pig_farm.entities.biomes import BiomeType
from big_pig_farm.game.world import FarmGrid, relayout_areas


class TestFarmArea:
    def test_interior_bounds(self):
        area = FarmArea(name="Test", biome=BiomeType.MEADOW, x1=0, y1=0, x2=10, y2=8)
        assert area.interior_x1 == 1
        assert area.interior_y1 == 1
        assert area.interior_x2 == 9
        assert area.interior_y2 == 7

    def test_contains(self):
        area = FarmArea(name="Test", biome=BiomeType.MEADOW, x1=5, y1=5, x2=15, y2=12)
        assert area.contains(5, 5)
        assert area.contains(10, 10)
        assert not area.contains(4, 5)
        assert not area.contains(16, 10)

    def test_contains_interior(self):
        area = FarmArea(name="Test", biome=BiomeType.MEADOW, x1=5, y1=5, x2=15, y2=12)
        assert area.contains_interior(6, 6)
        assert not area.contains_interior(5, 5)  # On wall

    def test_center(self):
        area = FarmArea(name="Test", biome=BiomeType.MEADOW, x1=0, y1=0, x2=10, y2=8)
        assert area.center_x == 5
        assert area.center_y == 4

    def test_grid_col_row_defaults(self):
        area = FarmArea(name="Test", biome=BiomeType.MEADOW, x1=0, y1=0, x2=10, y2=8)
        assert area.grid_col == 0
        assert area.grid_row == 0


class TestAddRoom:
    def test_starter_room(self):
        farm = FarmGrid.create_starter()
        assert len(farm.areas) == 1
        assert farm.areas[0].biome == BiomeType.MEADOW
        assert farm.areas[0].is_starter

    def test_add_second_room(self):
        farm = FarmGrid.create_starter()
        result = farm.add_room(BiomeType.BURROW)
        assert result is not None
        new_area, tunnels, offset_x, offset_y, _ = result
        assert new_area.biome == BiomeType.BURROW
        assert len(farm.areas) == 2
        assert len(farm.tunnels) >= 2  # At least two tunnels per connection

    def test_grid_slot_assignment(self):
        """New rooms get assigned reading-order grid slots (2 columns)."""
        farm = FarmGrid.create_starter()
        assert farm.areas[0].grid_col == 0
        assert farm.areas[0].grid_row == 0

        farm.add_room(BiomeType.BURROW)
        assert farm.areas[1].grid_col == 1
        assert farm.areas[1].grid_row == 0

        farm.add_room(BiomeType.GARDEN)
        assert farm.areas[2].grid_col == 0
        assert farm.areas[2].grid_row == 1

        farm.add_room(BiomeType.ALPINE)
        assert farm.areas[3].grid_col == 1
        assert farm.areas[3].grid_row == 1

    def test_tunnel_connects_areas(self):
        farm = FarmGrid.create_starter()
        result = farm.add_room(BiomeType.GARDEN)
        assert result is not None
        _, tunnels, _, _, _ = result
        area_ids = {a.id for a in farm.areas}
        for tunnel in farm.tunnels:
            assert tunnel.area_a_id in area_ids
            assert tunnel.area_b_id in area_ids
            assert len(tunnel.cells) > 0

    def test_tunnel_cells_are_walkable(self):
        farm = FarmGrid.create_starter()
        result = farm.add_room(BiomeType.ALPINE)
        assert result is not None
        for tunnel in farm.tunnels:
            walkable_cells = [(tx, ty) for tx, ty in tunnel.cells
                              if farm.cells[ty][tx].is_walkable]
            assert len(walkable_cells) > 0, "Tunnel should have walkable cells"

    def test_tunnel_barrier_walls(self):
        """Tunnels should have non-walkable barrier walls alongside the corridor."""
        farm = FarmGrid.create_starter()
        result = farm.add_room(BiomeType.BURROW)
        assert result is not None
        for tunnel in farm.tunnels:
            barrier_cells = [
                (tx, ty) for tx, ty in tunnel.cells
                if not farm.cells[ty][tx].is_walkable
                and farm.cells[ty][tx].is_tunnel
            ]
            assert len(barrier_cells) > 0, "Tunnel should have barrier wall cells"

    def test_pathfinding_across_rooms(self):
        farm = FarmGrid.create_starter()
        result = farm.add_room(BiomeType.BURROW)
        assert result is not None
        new_area, _, _, _, _ = result

        # Find walkable cells in each room
        start = farm.find_random_walkable_in_area(farm.areas[0].id)
        end = farm.find_random_walkable_in_area(new_area.id)
        assert start is not None
        assert end is not None

        path = farm.find_path(start, end)
        assert path is not None and len(path) > 0, "Should find path between rooms"

    def test_max_rooms(self):
        farm = FarmGrid.create_starter()
        biomes = list(BiomeType)
        # Add rooms until we hit the max
        rooms_added = 0
        for i in range(10):
            result = farm.add_room(biomes[i % len(biomes)])
            if result is None:
                break
            rooms_added += 1
        # We should be able to add at least a few rooms
        assert rooms_added >= 2

    def test_area_biome_lookup(self):
        farm = FarmGrid.create_starter()
        area = farm.areas[0]
        # A cell in the interior should return the correct biome
        biome = farm.get_biome_at(area.interior_x1, area.interior_y1)
        assert biome == BiomeType.MEADOW

    def test_capacity_grows_with_rooms(self):
        farm = FarmGrid.create_starter()
        cap1 = farm.capacity
        farm.add_room(BiomeType.BURROW)
        cap2 = farm.capacity
        assert cap2 > cap1


class TestThirdRoomLayout:
    def test_no_ghost_cells_after_third_room(self):
        """Adding a 3rd room repositions existing areas; old cells must be cleared."""
        farm = FarmGrid.create_starter()
        farm.add_room(BiomeType.BURROW)

        # Record room 0 position before 3rd room
        old_x1 = farm.areas[0].x1

        farm.add_room(BiomeType.GARDEN)

        # Room 0 should have shifted right (wider room 2 is in same column)
        new_x1 = farm.areas[0].x1
        assert new_x1 > old_x1, "Room 0 should shift right to center in wider column"

        # No cell outside any area or tunnel should have an area_id
        for y in range(farm.height):
            for x in range(farm.width):
                cell = farm.cells[y][x]
                if cell.area_id is not None and not cell.is_tunnel:
                    # Cell claims to belong to an area — verify it's within bounds
                    area = farm.get_area_by_id(cell.area_id)
                    assert area is not None, f"Cell ({x},{y}) has orphaned area_id"
                    assert area.contains(x, y), (
                        f"Ghost cell ({x},{y}) has area_id for {area.name} "
                        f"but is outside its bounds ({area.x1},{area.y1})-({area.x2},{area.y2})"
                    )


    def test_no_interior_walls_after_third_room(self):
        """Old border cells must become interior floors when rooms reposition."""
        from big_pig_farm.game.world import CellType
        farm = FarmGrid.create_starter()
        farm.add_room(BiomeType.BURROW)
        farm.add_room(BiomeType.GARDEN)

        for area in farm.areas:
            for x in range(area.interior_x1, area.interior_x2 + 1):
                for y in range(area.interior_y1, area.interior_y2 + 1):
                    cell = farm.cells[y][x]
                    if cell.is_tunnel:
                        continue
                    assert cell.cell_type != CellType.WALL, (
                        f"Interior cell ({x},{y}) in {area.name} is still WALL"
                    )

    def test_repair_clears_stale_interior_walls(self):
        """repair_area_cells fixes WALL cells stuck in room interiors."""
        from big_pig_farm.game.world import CellType
        farm = FarmGrid.create_starter()
        farm.add_room(BiomeType.BURROW)
        farm.add_room(BiomeType.GARDEN)

        # Manually corrupt: set an interior cell to WALL (simulates old bug)
        area = farm.areas[0]
        center_x, center_y = area.center_x, area.center_y
        farm.cells[center_y][center_x].cell_type = CellType.WALL
        farm.cells[center_y][center_x].is_walkable = False

        farm.repair_area_cells()

        cell = farm.cells[center_y][center_x]
        assert cell.cell_type == CellType.FLOOR
        assert cell.is_walkable


class TestAdjacentPairs:
    def test_two_rooms_horizontal(self):
        """Two rooms in col 0 and col 1 should be adjacent."""
        farm = FarmGrid.create_starter()
        farm.add_room(BiomeType.BURROW)
        pairs = farm._get_adjacent_pairs()
        assert len(pairs) == 1
        ids = {farm.areas[0].id, farm.areas[1].id}
        pair_ids = {pairs[0][0].id, pairs[0][1].id}
        assert ids == pair_ids

    def test_four_rooms_adjacency(self):
        """Four rooms in a 2x2 grid should have 4 adjacent pairs."""
        farm = FarmGrid.create_starter()
        farm.add_room(BiomeType.BURROW)
        farm.add_room(BiomeType.GARDEN)
        farm.add_room(BiomeType.ALPINE)
        pairs = farm._get_adjacent_pairs()
        # [0,0]-[1,0], [0,0]-[0,1], [1,0]-[1,1], [0,1]-[1,1]
        assert len(pairs) == 4


class TestRelayout:
    def test_relayout_noop_for_new_layout(self):
        """relayout_areas should be a no-op when grid slots are already set."""
        from big_pig_farm.game.state import GameState
        state = GameState()
        state.farm = FarmGrid.create_starter()
        state.farm.add_room(BiomeType.BURROW)

        # Positions before
        positions = [(a.x1, a.y1) for a in state.farm.areas]

        relayout_areas(state)

        # Positions unchanged — grid slots were already set by add_room
        for i, area in enumerate(state.farm.areas):
            assert (area.x1, area.y1) == positions[i]

    def test_relayout_assigns_grid_slots(self):
        """relayout_areas should assign grid_col/grid_row to legacy areas."""
        from big_pig_farm.game.state import GameState
        state = GameState()
        state.farm = FarmGrid.create_starter()

        # Simulate a legacy layout: add a second area with grid_col=0, grid_row=0
        area2 = FarmArea(
            name="Burrow Room", biome=BiomeType.BURROW,
            x1=70, y1=0, x2=131, y2=36,
            grid_col=0, grid_row=0,
        )
        state.farm.add_area(area2)

        relayout_areas(state)

        assert state.farm.areas[0].grid_col == 0
        assert state.farm.areas[0].grid_row == 0
        assert state.farm.areas[1].grid_col == 1
        assert state.farm.areas[1].grid_row == 0
