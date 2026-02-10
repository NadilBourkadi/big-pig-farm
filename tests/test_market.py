"""Tests for the economy/market module."""

import pytest

from big_pig_farm.data.config import ECONOMY
from big_pig_farm.economy.market import calculate_pig_value, sell_pig, get_rarity_multiplier, get_market_info
from big_pig_farm.entities.guinea_pig import GuineaPig, Gender, Position
from big_pig_farm.entities.genetics import Rarity
from big_pig_farm.game.state import GameState


def _make_pig(name="Test Pig", gender=Gender.MALE, age_days=5.0, **kwargs) -> GuineaPig:
    """Create a test pig."""
    return GuineaPig.create(
        name=name,
        gender=gender,
        position=Position(x=5.0, y=5.0),
        age_days=age_days,
        **kwargs,
    )


class TestRarityMultiplier:
    """Tests for rarity multiplier lookup."""

    def test_common_multiplier(self):
        assert get_rarity_multiplier(Rarity.COMMON) == 1.0

    def test_uncommon_multiplier(self):
        assert get_rarity_multiplier(Rarity.UNCOMMON) == ECONOMY.UNCOMMON_MULTIPLIER

    def test_legendary_multiplier(self):
        assert get_rarity_multiplier(Rarity.LEGENDARY) == ECONOMY.LEGENDARY_MULTIPLIER

    def test_unknown_defaults_to_one(self):
        assert get_rarity_multiplier("nonexistent") == 1.0


class TestPigValue:
    """Tests for pig value calculation."""

    def test_adult_has_base_value(self):
        pig = _make_pig(age_days=5.0)
        value = calculate_pig_value(pig)
        assert value >= ECONOMY.COMMON_PIG_VALUE * 0.5  # Health may reduce it

    def test_baby_worth_less(self):
        baby = _make_pig(age_days=0.5)
        adult = _make_pig(name="Adult", age_days=5.0)
        # Set both to full health
        baby.needs.health = 100
        adult.needs.health = 100
        assert calculate_pig_value(baby) < calculate_pig_value(adult)

    def test_senior_worth_less_than_adult(self):
        senior = _make_pig(age_days=100.0)
        adult = _make_pig(name="Adult", age_days=5.0)
        senior.needs.health = 100
        adult.needs.health = 100
        assert calculate_pig_value(senior) < calculate_pig_value(adult)

    def test_low_health_reduces_value(self):
        healthy = _make_pig(name="Healthy")
        sick = _make_pig(name="Sick")
        healthy.needs.health = 100
        sick.needs.health = 20
        assert calculate_pig_value(sick) < calculate_pig_value(healthy)

    def test_minimum_value_is_one(self):
        pig = _make_pig()
        pig.needs.health = 1
        value = calculate_pig_value(pig)
        assert value >= 1


class TestSellPig:
    """Tests for the sell_pig function."""

    def test_sell_removes_pig(self):
        state = GameState()
        pig = _make_pig()
        state.add_guinea_pig(pig)
        assert state.pig_count == 1

        sell_pig(state, pig)
        assert state.pig_count == 0

    def test_sell_adds_money(self):
        state = GameState()
        pig = _make_pig()
        state.add_guinea_pig(pig)
        initial_money = state.money

        result = sell_pig(state, pig)
        assert state.money == initial_money + result.total
        assert result.total > 0
        assert result.base_value > 0
        assert result.contract_bonus == 0
        assert result.matched_contract is None

    def test_sell_increments_sold_counter(self):
        state = GameState()
        pig = _make_pig()
        state.add_guinea_pig(pig)
        assert state.total_pigs_sold == 0

        sell_pig(state, pig)
        assert state.total_pigs_sold == 1

    def test_sell_logs_event(self):
        state = GameState()
        pig = _make_pig()
        state.add_guinea_pig(pig)
        initial_events = len(state.events)

        sell_pig(state, pig)
        assert len(state.events) > initial_events
        sale_events = [e for e in state.events if e.event_type == "sale"]
        assert len(sale_events) >= 1


class TestMarketInfo:
    """Tests for market info."""

    def test_empty_farm(self):
        state = GameState()
        info = get_market_info(state)
        assert info["total_value"] == 0
        assert info["pig_count"] == 0
        assert info["most_valuable"] is None

    def test_with_pigs(self):
        state = GameState()
        pig1 = _make_pig(name="Pig1")
        pig2 = _make_pig(name="Pig2", gender=Gender.FEMALE)
        state.add_guinea_pig(pig1)
        state.add_guinea_pig(pig2)

        info = get_market_info(state)
        assert info["pig_count"] == 2
        assert info["total_value"] > 0
        assert info["most_valuable"] is not None
