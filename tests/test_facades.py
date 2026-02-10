"""Tests for domain-specific state facades."""

from big_pig_farm.economy.market import calculate_pig_value
from big_pig_farm.entities.guinea_pig import GuineaPig, Gender, Position
from big_pig_farm.game.facades import PopulationFacade
from big_pig_farm.game.state import GameState


def _make_pig() -> GuineaPig:
    return GuineaPig.create(
        name="Facade",
        gender=Gender.FEMALE,
        position=Position(x=5.0, y=5.0),
        age_days=5.0,
    )


def test_population_facade_compatible_with_calculate_pig_value():
    """PopulationFacade duck-types into calculate_pig_value's state param."""
    state = GameState()
    facade = PopulationFacade(state)
    pig = _make_pig()

    value = calculate_pig_value(pig, facade)
    assert isinstance(value, int)
    assert value > 0
