"""Tests for biome-aware wandering direction bias."""

from collections import Counter

from big_pig_farm.data.config import BEHAVIOR
from big_pig_farm.entities.areas import FarmArea
from big_pig_farm.entities.biomes import BiomeType
from big_pig_farm.entities.genetics import BaseColor, Genotype
from big_pig_farm.entities.guinea_pig import Gender, GuineaPig, Position
from big_pig_farm.game.world import FarmGrid


def _make_grid_with_areas() -> FarmGrid:
    """Create a grid with two areas: Meadow (left) and Burrow (right)."""
    grid = FarmGrid(width=140, height=40, tier=1)
    meadow = FarmArea(
        name="Meadow Room", biome=BiomeType.MEADOW,
        x1=0, y1=0, x2=60, y2=39,
    )
    burrow = FarmArea(
        name="Burrow Room", biome=BiomeType.BURROW,
        x1=70, y1=0, x2=139, y2=39,
    )
    grid.add_area(meadow)
    grid.add_area(burrow)
    return grid


def _make_pig(
    base_color: BaseColor = BaseColor.BLACK,
    preferred_biome: str | None = "meadow",
    position: Position | None = None,
) -> GuineaPig:
    """Create a pig with a specific base color and preferred biome."""
    color_genotypes = {
        BaseColor.BLACK: {"e_locus": ("E", "E"), "b_locus": ("B", "B"), "d_locus": ("D", "D")},
        BaseColor.CHOCOLATE: {"e_locus": ("E", "E"), "b_locus": ("b", "b"), "d_locus": ("D", "D")},
        BaseColor.GOLDEN: {"e_locus": ("e", "e"), "b_locus": ("B", "B"), "d_locus": ("D", "D")},
        BaseColor.CREAM: {"e_locus": ("e", "e"), "b_locus": ("b", "b"), "d_locus": ("D", "D")},
    }
    loci = color_genotypes[base_color]
    genotype = Genotype(
        e_locus=loci["e_locus"], b_locus=loci["b_locus"],
        s_locus=("S", "S"), c_locus=("C", "C"),
        r_locus=("r", "r"), d_locus=loci["d_locus"],
    )
    pig = GuineaPig.create(
        name="Test", gender=Gender.MALE,
        position=position or Position(x=5.0, y=5.0),
        age_days=5.0, genotype=genotype,
    )
    pig.preferred_biome = preferred_biome
    return pig


class TestFindAreasByBiome:
    """Tests for FarmGrid.find_areas_by_biome()."""

    def test_returns_matching_areas(self):
        grid = _make_grid_with_areas()
        meadows = grid.find_areas_by_biome("meadow")
        assert len(meadows) == 1
        assert meadows[0].biome == BiomeType.MEADOW

    def test_returns_empty_for_absent_biome(self):
        grid = _make_grid_with_areas()
        assert grid.find_areas_by_biome("tropical") == []

    def test_cache_invalidated_on_area_add(self):
        grid = _make_grid_with_areas()
        # Warm the cache
        assert len(grid.find_areas_by_biome("meadow")) == 1
        assert grid.find_areas_by_biome("tropical") == []
        # Add a tropical area — cache should be rebuilt
        tropical = FarmArea(
            name="Tropical Room", biome=BiomeType.TROPICAL,
            x1=0, y1=0, x2=10, y2=10,
        )
        grid.add_area(tropical)
        assert len(grid.find_areas_by_biome("tropical")) == 1

    def test_multiple_areas_same_biome(self):
        grid = FarmGrid(width=200, height=40, tier=1)
        for i in range(3):
            grid.add_area(FarmArea(
                name=f"Meadow {i}", biome=BiomeType.MEADOW,
                x1=i * 65, y1=0, x2=i * 65 + 60, y2=39,
            ))
        assert len(grid.find_areas_by_biome("meadow")) == 3


class TestGetBiomeWanderTarget:
    """Tests for BehaviorController._get_biome_wander_target()."""

    def _make_controller(self, grid):
        """Create a minimal BehaviorController with the given grid."""
        from unittest.mock import MagicMock
        state = MagicMock()
        state.farm = grid
        from big_pig_farm.simulation.behavior import BehaviorController
        return BehaviorController(state)

    def test_color_takes_priority_over_preferred_biome(self):
        grid = _make_grid_with_areas()
        controller = self._make_controller(grid)
        # Black pig prefers burrow, but BLACK's signature biome is Meadow
        pig = _make_pig(base_color=BaseColor.BLACK, preferred_biome="burrow",
                        position=Position(x=5.0, y=5.0))
        target, is_color = controller._get_biome_wander_target(pig)
        assert target is not None
        assert target.biome == BiomeType.MEADOW  # Color wins over preferred_biome
        assert is_color is True

    def test_returns_none_when_no_match(self):
        grid = _make_grid_with_areas()
        controller = self._make_controller(grid)
        # Golden maps to Garden (not on grid), preferred=tropical (also not on grid)
        pig = _make_pig(preferred_biome="tropical", base_color=BaseColor.GOLDEN)
        target, is_color = controller._get_biome_wander_target(pig)
        assert target is None

    def test_color_match_primary(self):
        grid = _make_grid_with_areas()
        controller = self._make_controller(grid)
        # Chocolate pig — signature biome is Burrow, which is on the grid
        pig = _make_pig(base_color=BaseColor.CHOCOLATE, preferred_biome=None)
        target, is_color = controller._get_biome_wander_target(pig)
        assert target is not None
        assert target.biome == BiomeType.BURROW
        assert is_color is True

    def test_falls_back_to_preferred_biome(self):
        grid = _make_grid_with_areas()
        controller = self._make_controller(grid)
        # Golden pig — Garden not on grid, falls back to preferred_biome=burrow
        pig = _make_pig(base_color=BaseColor.GOLDEN, preferred_biome="burrow")
        target, is_color = controller._get_biome_wander_target(pig)
        assert target is not None
        assert target.biome == BiomeType.BURROW
        assert is_color is False  # Fallback, not color match

    def test_no_bias_when_no_preference_and_no_color_match(self):
        grid = _make_grid_with_areas()
        controller = self._make_controller(grid)
        # Golden pig, no preferred biome — Garden not on farm
        pig = _make_pig(base_color=BaseColor.GOLDEN, preferred_biome=None)
        target, is_color = controller._get_biome_wander_target(pig)
        assert target is None

    def test_picks_closest_area_when_multiple(self):
        grid = FarmGrid(width=200, height=40, tier=1)
        far_meadow = FarmArea(
            name="Meadow Far", biome=BiomeType.MEADOW,
            x1=130, y1=0, x2=199, y2=39,
        )
        near_meadow = FarmArea(
            name="Meadow Near", biome=BiomeType.MEADOW,
            x1=0, y1=0, x2=60, y2=39,
        )
        grid.add_area(far_meadow)
        grid.add_area(near_meadow)
        controller = self._make_controller(grid)
        pig = _make_pig(preferred_biome="meadow", position=Position(x=10.0, y=10.0))
        target, _is_color = controller._get_biome_wander_target(pig)
        assert target.name == "Meadow Near"


class TestBiasWanderDirections:
    """Tests for BehaviorController._bias_wander_directions()."""

    def _make_controller(self, grid):
        from unittest.mock import MagicMock
        state = MagicMock()
        state.farm = grid
        from big_pig_farm.simulation.behavior import BehaviorController
        return BehaviorController(state)

    def test_outside_bias_toward_area(self):
        """A pig outside the target area should have homeward directions weighted higher."""
        grid = _make_grid_with_areas()
        controller = self._make_controller(grid)
        # Target is burrow (right side, center ~104, 19)
        target_area = grid.find_areas_by_biome("burrow")[0]
        # Pig is in meadow (left side)
        pig = _make_pig(position=Position(x=10.0, y=20.0))

        # Sample many times and count direction frequencies
        counts: Counter[tuple[int, int]] = Counter()
        for _ in range(2000):
            result = controller._bias_wander_directions(pig, target_area)
            counts[result[0]] += 1  # First direction in weighted list

        # Right (1, 0) should be picked much more often than left (-1, 0)
        assert counts[(1, 0)] > counts[(-1, 0)] * 2

    def test_inside_bias_away_from_edge(self):
        """A pig inside the target area near the left edge should be biased rightward."""
        grid = _make_grid_with_areas()
        controller = self._make_controller(grid)
        target_area = grid.find_areas_by_biome("meadow")[0]
        # Pig is near the left wall of meadow
        pig = _make_pig(position=Position(x=2.0, y=20.0))

        counts: Counter[tuple[int, int]] = Counter()
        for _ in range(2000):
            result = controller._bias_wander_directions(pig, target_area)
            counts[result[0]] += 1

        # Right (1, 0) has more room → should be favored over left (-1, 0)
        assert counts[(1, 0)] > counts[(-1, 0)]

    def test_no_crash_when_pig_at_center(self):
        """Pig at center of area should not crash and should return 4 directions."""
        grid = _make_grid_with_areas()
        controller = self._make_controller(grid)
        target_area = grid.find_areas_by_biome("meadow")[0]
        pig = _make_pig(position=Position(
            x=float(target_area.center_x),
            y=float(target_area.center_y),
        ))
        result = controller._bias_wander_directions(pig, target_area)
        assert len(result) == 4

    def test_returns_all_four_directions(self):
        """All four cardinal directions should appear across many samples."""
        grid = _make_grid_with_areas()
        controller = self._make_controller(grid)
        target_area = grid.find_areas_by_biome("burrow")[0]
        pig = _make_pig(position=Position(x=10.0, y=20.0))

        seen: set[tuple[int, int]] = set()
        for _ in range(200):
            result = controller._bias_wander_directions(pig, target_area)
            seen.update(result)

        assert len(seen) == 4
