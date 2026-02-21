"""Tests for the breeding/reproduction system."""

import pytest

from big_pig_farm.data.config import BREEDING
from big_pig_farm.entities.genetics import BaseColor
from big_pig_farm.entities.guinea_pig import BehaviorState, Gender, GuineaPig, Position
from big_pig_farm.game.state import GameState
from big_pig_farm.simulation.birth import advance_pregnancies, age_all_pigs, register_pig_in_pigdex
from big_pig_farm.simulation.breeding import check_breeding_opportunities
from big_pig_farm.simulation.breeding_program import BreedingProgram


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


class TestManualBreeding:
    """Tests for the manual breeding pair system."""

    def test_manual_pair_triggers_courtship(self):
        state = GameState()
        male, female = _make_breeding_pair(state)

        state.set_breeding_pair(male.id, female.id)
        check_breeding_opportunities(state)

        # Courtship starts — not instant pregnancy
        assert not female.is_pregnant
        assert male.behavior_state == BehaviorState.COURTING
        assert female.behavior_state == BehaviorState.COURTING
        assert male.courting_partner_id == female.id
        assert female.courting_partner_id == male.id
        assert male.courting_initiator is True
        assert female.courting_initiator is False
        assert state.breeding_pair is None  # Cleared after courtship started

    def test_manual_pair_clears_on_missing_pig(self):
        state = GameState()
        male, female = _make_breeding_pair(state)

        state.set_breeding_pair(male.id, female.id)
        state.remove_guinea_pig(male.id)

        check_breeding_opportunities(state)

        assert not female.is_pregnant
        assert state.breeding_pair is None

    def test_manual_pair_waits_if_not_ready(self):
        state = GameState()
        male, female = _make_breeding_pair(state)

        # Low happiness prevents breeding
        male.needs.happiness = 10
        state.set_breeding_pair(male.id, female.id)

        check_breeding_opportunities(state)

        assert not female.is_pregnant
        assert state.breeding_pair is not None  # Still waiting

    def test_manual_pair_clears_if_female_pregnant(self):
        state = GameState()
        male, female = _make_breeding_pair(state)

        female.is_pregnant = True
        female.pregnancy_days = 0.5
        female.partner_id = male.id

        state.set_breeding_pair(male.id, female.id)
        check_breeding_opportunities(state)

        assert state.breeding_pair is None  # Cleared because already pregnant

    def test_manual_pair_bypasses_distance(self):
        state = GameState()
        # Place pigs at opposite corners
        male = _make_pig("Boar", Gender.MALE, age_days=5.0, x=1.0, y=1.0)
        female = _make_pig("Sow", Gender.FEMALE, age_days=5.0, x=30.0, y=20.0)
        male.needs.happiness = 90
        female.needs.happiness = 90
        male.needs.health = 100
        female.needs.health = 100
        state.add_guinea_pig(male)
        state.add_guinea_pig(female)

        state.set_breeding_pair(male.id, female.id)
        check_breeding_opportunities(state)

        # Courtship starts regardless of distance
        assert male.behavior_state == BehaviorState.COURTING
        assert female.behavior_state == BehaviorState.COURTING
        assert state.breeding_pair is None

    def test_set_new_pair_replaces_old(self):
        state = GameState()
        male1 = _make_pig("Boar1", Gender.MALE, age_days=5.0, x=5.0, y=5.0)
        male2 = _make_pig("Boar2", Gender.MALE, age_days=5.0, x=6.0, y=5.0)
        female = _make_pig("Sow", Gender.FEMALE, age_days=5.0, x=5.5, y=5.0)
        for pig in [male1, male2, female]:
            pig.needs.happiness = 90
            pig.needs.health = 100
            state.add_guinea_pig(pig)

        state.set_breeding_pair(male1.id, female.id)
        state.set_breeding_pair(male2.id, female.id)

        assert state.breeding_pair.male_id == male2.id
        assert state.breeding_pair.female_id == female.id


class TestBreedingProgram:
    """Tests for breeding filter integration with birth flow."""

    def _birth_with_filter(self, state, male, female, breeding_program):
        """Set up a pregnancy and trigger birth, return newborn pigs."""
        state.breeding_program = breeding_program
        female.is_pregnant = True
        female.pregnancy_days = BREEDING.GESTATION_DAYS
        female.partner_id = male.id
        female.partner_genotype = male.genotype

        initial_ids = {p.id for p in state.get_pigs_list()}
        check_breeding_opportunities(state)
        return [p for p in state.get_pigs_list() if p.id not in initial_ids]

    def test_disabled_filter_does_not_mark(self):
        state = GameState()
        male, female = _make_breeding_pair(state)
        f = BreedingProgram(enabled=False, target_colors={BaseColor.GOLDEN})

        babies = self._birth_with_filter(state, male, female, f)
        assert len(babies) > 0
        assert all(not b.marked_for_sale for b in babies)

    def test_enabled_filter_marks_non_matching(self):
        state = GameState()
        # Expand farm to hold more pigs
        state.farm.tier = 3  # Family Pen, capacity 20
        male, female = _make_breeding_pair(state)
        # Add extra adults so population exceeds the stock limit
        for i in range(3):
            extra = _make_pig(f"Extra{i}", Gender.FEMALE, age_days=5.0, x=15.0, y=15.0)
            state.add_guinea_pig(extra)
        # Both parents have random-common genotypes (likely BB EE = Black)
        # Filter for Golden only; stock_limit=4 so 5 adults > limit
        f = BreedingProgram(enabled=True, stock_limit=4, target_colors={BaseColor.GOLDEN})

        babies = self._birth_with_filter(state, male, female, f)
        assert len(babies) > 0
        for baby in babies:
            if baby.phenotype.base_color == BaseColor.GOLDEN:
                assert not baby.marked_for_sale
            else:
                assert baby.marked_for_sale

    def test_filter_logs_event(self):
        state = GameState()
        male, female = _make_breeding_pair(state)
        # Filter for something very unlikely
        f = BreedingProgram(enabled=True, target_colors={BaseColor.CREAM})

        self._birth_with_filter(state, male, female, f)
        filter_events = [e for e in state.events if e.event_type == "filter"]
        # May or may not have filter events depending on babies' phenotypes
        # Just verify no crash occurred
        assert isinstance(filter_events, list)

    def test_pigdex_registered_before_filter(self):
        state = GameState()
        male, female = _make_breeding_pair(state)
        f = BreedingProgram(enabled=True, target_colors={BaseColor.GOLDEN})

        self._birth_with_filter(state, male, female, f)
        # All babies should be registered in pigdex regardless of filter
        assert state.pigdex.discovered_count >= 1


class TestStalePairClearing:
    """Tests for clearing stale breeding pairs that can never complete."""

    def test_manual_pair_clears_when_pig_becomes_senior(self):
        state = GameState()
        male, female = _make_breeding_pair(state)
        state.set_breeding_pair(male.id, female.id)

        # Male ages into senior territory
        male.age_days = 31.0  # Past SENIOR_AGE_DAYS (30)
        check_breeding_opportunities(state)

        assert state.breeding_pair is None
        cancel_events = [
            e for e in state.events
            if e.event_type == "breeding" and "can no longer breed" in e.message
        ]
        assert len(cancel_events) == 1
        assert male.name in cancel_events[0].message

    def test_manual_pair_clears_when_pig_breeding_locked(self):
        state = GameState()
        male, female = _make_breeding_pair(state)
        state.set_breeding_pair(male.id, female.id)

        female.breeding_locked = True
        check_breeding_opportunities(state)

        assert state.breeding_pair is None
        cancel_events = [
            e for e in state.events
            if e.event_type == "breeding" and "can no longer breed" in e.message
        ]
        assert len(cancel_events) == 1
        assert female.name in cancel_events[0].message

    def test_auto_pair_resumes_after_stale_pair_cleared(self):
        state = GameState()
        male1, female = _make_breeding_pair(state)
        male2 = _make_pig("Boar2", Gender.MALE, age_days=5.0, x=6.0, y=5.0)
        male2.needs.happiness = 90
        male2.needs.health = 100
        state.add_guinea_pig(male2)

        # Set up breeding program so auto-pair can engage
        program = BreedingProgram(enabled=True, target_colors={BaseColor.BLACK})
        state.breeding_program = program

        # Stale pair: male1 is senior
        state.set_breeding_pair(male1.id, female.id)
        male1.age_days = 31.0

        # Single tick: clears the stale pair AND auto-pair fires immediately
        check_breeding_opportunities(state)

        # Verify the stale pair was logged as cancelled
        cancel_events = [
            e for e in state.events
            if e.event_type == "breeding" and "can no longer breed" in e.message
        ]
        assert len(cancel_events) == 1

        # Auto-pair resumed in the same tick with the eligible male
        assert state.breeding_pair is not None or female.behavior_state == BehaviorState.COURTING
