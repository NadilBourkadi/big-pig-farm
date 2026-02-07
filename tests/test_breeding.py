"""Tests for the breeding/reproduction system."""

import pytest
from datetime import datetime, timedelta

from big_pig_farm.data.config import BREEDING
from big_pig_farm.entities.guinea_pig import GuineaPig, Gender, Position, BehaviorState
from big_pig_farm.entities.genetics import Genotype
from big_pig_farm.simulation.breeding import (
    check_breeding_opportunities,
    advance_pregnancies,
    age_all_pigs,
    register_pig_in_pigdex,
)
from big_pig_farm.game.state import GameState


def _make_pig(name, gender, age_days=5.0, x=5.0, y=5.0, **kwargs) -> GuineaPig:
    """Create a test pig."""
    return GuineaPig.create(
        name=name,
        gender=gender,
        position=Position(x=x, y=y),
        age_days=age_days,
        **kwargs,
    )


def _make_breeding_pair(state: GameState) -> tuple[GuineaPig, GuineaPig]:
    """Create an eligible male-female pair close together."""
    male = _make_pig("Boar", Gender.MALE, age_days=5.0, x=5.0, y=5.0)
    female = _make_pig("Sow", Gender.FEMALE, age_days=5.0, x=5.5, y=5.0)
    # Ensure they're happy enough to breed
    male.needs.happiness = 90
    female.needs.happiness = 90
    male.needs.health = 100
    female.needs.health = 100
    state.add_guinea_pig(male)
    state.add_guinea_pig(female)
    return male, female


class TestPregnancyProgression:
    """Tests for pregnancy timing."""

    def test_advance_pregnancies(self):
        state = GameState()
        female = _make_pig("Mama", Gender.FEMALE)
        female.is_pregnant = True
        female.pregnancy_days = 0.0
        state.add_guinea_pig(female)

        advance_pregnancies(state, 24.0)  # 24 game hours = 1 day
        assert female.pregnancy_days == pytest.approx(1.0)

    def test_advance_skips_non_pregnant(self):
        state = GameState()
        pig = _make_pig("Normal", Gender.FEMALE)
        pig.is_pregnant = False
        pig.pregnancy_days = 0.0
        state.add_guinea_pig(pig)

        advance_pregnancies(state, 24.0)
        assert pig.pregnancy_days == 0.0


class TestBirth:
    """Tests for the birth process."""

    def test_birth_occurs_after_gestation(self):
        state = GameState()
        male, female = _make_breeding_pair(state)

        female.is_pregnant = True
        female.pregnancy_days = BREEDING.GESTATION_DAYS  # Ready to give birth
        female.partner_id = male.id

        initial_count = state.pig_count
        check_breeding_opportunities(state)

        assert state.pig_count > initial_count
        assert not female.is_pregnant

    def test_birth_does_not_exceed_capacity(self):
        state = GameState()
        male, female = _make_breeding_pair(state)

        # Fill the farm to near capacity
        capacity = state.capacity
        for i in range(capacity - 2):
            filler = _make_pig(f"Filler{i}", Gender.MALE, x=float(3 + i % 10), y=float(3 + i // 10))
            state.add_guinea_pig(filler)

        female.is_pregnant = True
        female.pregnancy_days = BREEDING.GESTATION_DAYS
        female.partner_id = male.id

        check_breeding_opportunities(state)
        assert state.pig_count <= capacity

    def test_birth_without_father_cancels_pregnancy(self):
        state = GameState()
        female = _make_pig("Solo", Gender.FEMALE)
        female.is_pregnant = True
        female.pregnancy_days = BREEDING.GESTATION_DAYS
        female.partner_id = None  # No father
        state.add_guinea_pig(female)

        initial_count = state.pig_count
        check_breeding_opportunities(state)

        # No birth, pregnancy cancelled
        assert state.pig_count == initial_count
        assert not female.is_pregnant

    def test_birth_logs_event(self):
        state = GameState()
        male, female = _make_breeding_pair(state)

        female.is_pregnant = True
        female.pregnancy_days = BREEDING.GESTATION_DAYS
        female.partner_id = male.id

        initial_events = len(state.events)
        check_breeding_opportunities(state)

        birth_events = [e for e in state.events if e.event_type == "birth"]
        assert len(birth_events) >= 1

    def test_babies_have_parents_set(self):
        state = GameState()
        male, female = _make_breeding_pair(state)

        female.is_pregnant = True
        female.pregnancy_days = BREEDING.GESTATION_DAYS
        female.partner_id = male.id

        initial_ids = {p.id for p in state.get_pigs_list()}
        check_breeding_opportunities(state)

        new_pigs = [p for p in state.get_pigs_list() if p.id not in initial_ids]
        assert len(new_pigs) > 0

        for baby in new_pigs:
            assert baby.mother_id == female.id
            assert baby.father_id == male.id
            assert baby.age_days == 0


class TestAging:
    """Tests for the aging system."""

    def test_pigs_age(self):
        state = GameState()
        pig = _make_pig("Aging", Gender.MALE, age_days=5.0)
        state.add_guinea_pig(pig)

        age_all_pigs(state, 24.0)  # 24 hours = 1 day
        assert pig.age_days == pytest.approx(6.0)

    def test_young_pigs_dont_die(self):
        state = GameState()
        pig = _make_pig("Young", Gender.MALE, age_days=5.0)
        state.add_guinea_pig(pig)

        deaths = age_all_pigs(state, 24.0)
        assert len(deaths) == 0
        assert state.pig_count == 1


class TestPigdexRegistration:
    """Tests for pigdex registration via breeding module."""

    def test_register_new_discovery(self):
        state = GameState()
        pig = _make_pig("Discoverer", Gender.MALE)

        initial_money = state.money
        register_pig_in_pigdex(state, pig)

        # Should have registered and potentially got a reward
        assert state.pigdex.discovered_count >= 1

    def test_duplicate_registration_no_reward(self):
        state = GameState()
        pig1 = _make_pig("First", Gender.MALE)
        pig2 = _make_pig("Second", Gender.FEMALE)

        # Same genotype → same phenotype key
        pig2._phenotype = pig1.phenotype

        register_pig_in_pigdex(state, pig1)
        money_after_first = state.money

        register_pig_in_pigdex(state, pig2)
        # No additional reward for duplicate
        assert state.money == money_after_first
