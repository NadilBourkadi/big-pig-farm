"""Tests for area layout, tunnels, and multi-room pathfinding."""

import pytest

from big_pig_farm.entities.areas import FarmArea, TunnelConnection
from big_pig_farm.entities.biomes import BiomeType
from big_pig_farm.game.world import FarmGrid


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
        new_area, tunnels, offset_x, offset_y = result
        assert new_area.biome == BiomeType.BURROW
        assert len(farm.areas) == 2
        assert len(farm.tunnels) == 2  # Two tunnels per connection

    def test_tunnel_connects_areas(self):
        farm = FarmGrid.create_starter()
        result = farm.add_room(BiomeType.GARDEN)
        assert result is not None
        _, tunnels, _, _ = result
        area_ids = {a.id for a in farm.areas}
        for tunnel in tunnels:
            assert tunnel.area_a_id in area_ids
            assert tunnel.area_b_id in area_ids
            assert len(tunnel.cells) > 0

    def test_tunnel_cells_are_walkable(self):
        farm = FarmGrid.create_starter()
        result = farm.add_room(BiomeType.ALPINE)
        assert result is not None
        _, tunnels, _, _ = result
        for tunnel in tunnels:
            for tx, ty in tunnel.cells:
                assert farm.is_walkable(tx, ty), f"Tunnel cell ({tx}, {ty}) not walkable"
                assert farm.cells[ty][tx].is_tunnel

    def test_pathfinding_across_rooms(self):
        farm = FarmGrid.create_starter()
        result = farm.add_room(BiomeType.BURROW)
        assert result is not None
        new_area, _, _, _ = result

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
