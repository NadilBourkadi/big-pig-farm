"""Tests for pig rescue from non-walkable cells."""

from big_pig_farm.entities.genetics import Genotype, calculate_phenotype
from big_pig_farm.entities.guinea_pig import BehaviorState, Gender, GuineaPig, Position
from big_pig_farm.game.state import GameState
from big_pig_farm.game.world import FarmGrid
from big_pig_farm.simulation.behavior import BehaviorController


def _make_state() -> GameState:
    farm = FarmGrid.create_starter()
    return GameState(farm=farm)


def _make_pig(x: float = 5.0, y: float = 5.0) -> GuineaPig:
    genotype = Genotype.random()
    phenotype = calculate_phenotype(genotype)
    return GuineaPig(
        name="TestPig",
        genotype=genotype,
        phenotype=phenotype,
        gender=Gender.MALE,
        position=Position(x=x, y=y),
    )


def _make_controller(state: GameState) -> BehaviorController:
    return BehaviorController(state)


class TestRescueFromNonWalkable:
    """Tests for _rescue_to_walkable and rescue_non_walkable_pigs."""

    def test_pig_rescued_to_walkable_cell(self):
        """A pig on a wall cell should be moved to a walkable cell."""
        state = _make_state()
        controller = _make_controller(state)
        farm = state.farm

        # Place pig on a wall cell (0, 0)
        pig = _make_pig(0.0, 0.0)
        state.add_guinea_pig(pig)
        assert not farm.is_walkable(0, 0)

        controller.rescue_non_walkable_pigs(state.get_pigs_list())

        gx, gy = int(pig.position.x), int(pig.position.y)
        assert farm.is_walkable(gx, gy)

    def test_rescue_sets_idle_state(self):
        """Rescued pigs should have IDLE state and cleared navigation."""
        state = _make_state()
        controller = _make_controller(state)

        pig = _make_pig(0.0, 0.0)
        pig.behavior_state = BehaviorState.WANDERING
        pig.path = [(1, 1), (2, 2)]
        pig.target_position = Position(x=2.0, y=2.0)
        state.add_guinea_pig(pig)

        controller.rescue_non_walkable_pigs([pig])

        assert pig.behavior_state == BehaviorState.IDLE
        assert pig.path == []
        assert pig.target_position is None
        assert pig.target_facility_id is None

    def test_pigs_on_walkable_cells_unchanged(self):
        """Pigs already on walkable cells should not be moved."""
        state = _make_state()
        controller = _make_controller(state)

        # Interior cell (5, 5) is walkable
        pig = _make_pig(5.0, 5.0)
        state.add_guinea_pig(pig)

        controller.rescue_non_walkable_pigs([pig])

        assert pig.position.x == 5.0
        assert pig.position.y == 5.0

    def test_rescue_multiple_pigs(self):
        """Multiple stuck pigs should all be rescued."""
        state = _make_state()
        controller = _make_controller(state)
        farm = state.farm

        pigs = [_make_pig(0.0, 0.0), _make_pig(0.0, 1.0)]
        for pig in pigs:
            state.add_guinea_pig(pig)

        controller.rescue_non_walkable_pigs(pigs)

        for pig in pigs:
            gx, gy = int(pig.position.x), int(pig.position.y)
            assert farm.is_walkable(gx, gy)

    def test_rescue_logs_behavior(self):
        """Rescued pigs should have a behavior log entry."""
        state = _make_state()
        controller = _make_controller(state)

        pig = _make_pig(0.0, 0.0)
        state.add_guinea_pig(pig)

        controller.rescue_non_walkable_pigs([pig])

        assert any("Rescued" in entry for entry in pig.behavior_log)
