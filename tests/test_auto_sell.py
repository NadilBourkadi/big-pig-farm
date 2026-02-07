"""Tests for the auto-sell marked pigs feature."""

from big_pig_farm.entities.guinea_pig import GuineaPig, Gender, Position
from big_pig_farm.game.state import GameState
from big_pig_farm.simulation.breeding import sell_marked_adults


class TestAutoSell:
    """Tests for marking pigs for auto-sell at adulthood."""

    def _make_pig(self, age_days: float = 0.0, marked: bool = False) -> GuineaPig:
        pig = GuineaPig.create(
            name="TestPig",
            gender=Gender.MALE,
            position=Position(x=5.0, y=5.0),
            age_days=age_days,
        )
        pig.marked_for_sale = marked
        return pig

    def test_default_not_marked(self):
        """New pigs should not be marked for sale by default."""
        pig = GuineaPig.create(name="Squeaky", gender=Gender.FEMALE)
        assert pig.marked_for_sale is False

    def test_auto_sell_triggers(self):
        """A marked pig that has reached adulthood should be auto-sold."""
        state = GameState()
        pig = self._make_pig(age_days=4.0, marked=True)
        state.add_guinea_pig(pig)
        initial_money = state.money

        sold = sell_marked_adults(state)

        assert len(sold) == 1
        assert sold[0][0] == "TestPig"
        assert sold[0][1] > 0  # sale price
        assert state.money > initial_money
        assert state.get_guinea_pig(pig.id) is None

    def test_unmarked_not_sold(self):
        """An unmarked adult pig should not be auto-sold."""
        state = GameState()
        pig = self._make_pig(age_days=5.0, marked=False)
        state.add_guinea_pig(pig)

        sold = sell_marked_adults(state)

        assert len(sold) == 0
        assert state.get_guinea_pig(pig.id) is not None

    def test_marked_baby_not_sold_prematurely(self):
        """A marked pig that is still a baby should not be sold yet."""
        state = GameState()
        pig = self._make_pig(age_days=1.0, marked=True)
        state.add_guinea_pig(pig)

        sold = sell_marked_adults(state)

        assert len(sold) == 0
        assert state.get_guinea_pig(pig.id) is not None
