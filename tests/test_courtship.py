"""Tests for physical courtship and social affinity systems."""

from uuid import uuid4

from big_pig_farm.data.config import BEHAVIOR
from big_pig_farm.entities.genetics import BaseColor
from big_pig_farm.entities.guinea_pig import BehaviorState, Gender, GuineaPig, Position
from big_pig_farm.game.state import GameState
from big_pig_farm.simulation.behavior_controller import BehaviorController
from big_pig_farm.simulation.behavior_decision import make_decision
from big_pig_farm.simulation.breeding import (
    _initiate_courtship,
    check_breeding_opportunities,
    clear_courtship,
    start_pregnancy_from_courtship,
)
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


def _make_breedable_pair(state: GameState, close=True) -> tuple[GuineaPig, GuineaPig]:
    """Create an eligible male-female pair, optionally close together."""
    male = _make_pig("Boar", Gender.MALE, x=5.0, y=5.0)
    female = _make_pig("Sow", Gender.FEMALE, x=5.5 if close else 30.0, y=5.0 if close else 20.0)
    male.needs.happiness = 90
    female.needs.happiness = 90
    male.needs.health = 100
    female.needs.health = 100
    state.add_guinea_pig(male)
    state.add_guinea_pig(female)
    return male, female


class TestCourtshipInitiation:
    """Tests for courtship being initiated instead of instant pregnancy."""

    def test_manual_pair_starts_courtship(self):
        state = GameState()
        male, female = _make_breedable_pair(state)

        state.set_breeding_pair(male.id, female.id)
        check_breeding_opportunities(state)

        assert not female.is_pregnant
        assert male.behavior_state == BehaviorState.COURTING
        assert female.behavior_state == BehaviorState.COURTING
        assert male.courting_partner_id == female.id
        assert female.courting_partner_id == male.id
        assert male.courting_initiator is True
        assert female.courting_initiator is False

    def test_already_courting_pig_excluded_from_new_breeding(self):
        state = GameState()
        male, female = _make_breedable_pair(state)

        # Put male in courting state with a different (fake) partner
        male.behavior_state = BehaviorState.COURTING
        male.courting_partner_id = uuid4()

        state.set_breeding_pair(male.id, female.id)
        check_breeding_opportunities(state)

        # Should not have started new courtship
        assert female.behavior_state != BehaviorState.COURTING

    def test_initiate_courtship_clears_movement(self):
        state = GameState()
        male, female = _make_breedable_pair(state)

        male.path = [(10, 10), (11, 11)]
        male.target_facility_id = uuid4()

        _initiate_courtship(male, female, state)

        assert male.path == []
        assert male.target_facility_id is None
        assert female.path == []


class TestCourtshipCompletion:
    """Tests for courtship completing and starting pregnancy."""

    def test_courtship_completes_to_pregnancy(self):
        state = GameState()
        male, female = _make_breedable_pair(state)

        _initiate_courtship(male, female, state)

        # Simulate courtship completion
        start_pregnancy_from_courtship(male, female, state)

        assert female.is_pregnant
        assert female.partner_id == male.id
        assert female.partner_genotype == male.genotype
        assert female.partner_name == male.name
        # Courtship fields cleared
        assert male.courting_partner_id is None
        assert female.courting_partner_id is None
        assert male.behavior_state == BehaviorState.IDLE
        assert female.behavior_state == BehaviorState.IDLE

    def test_together_timer_advances_when_adjacent(self):
        state = GameState()
        male, female = _make_breedable_pair(state)

        _initiate_courtship(male, female, state)
        # Place them adjacent (no path remaining)
        male.path = []
        female.path = []

        controller = BehaviorController(state)
        controller.collision.rebuild_spatial_grid()

        # Simulate ticks
        for _ in range(10):
            controller._update_current_behavior(male, 0.5)

        assert male.courting_timer > 0.0
        assert male.courting_timer == female.courting_timer

    def test_courtship_queues_completion_after_timer(self):
        state = GameState()
        male, female = _make_breedable_pair(state)

        _initiate_courtship(male, female, state)
        male.path = []
        female.path = []

        controller = BehaviorController(state)
        controller.collision.rebuild_spatial_grid()

        # Advance timer past the threshold
        ticks_needed = int(BEHAVIOR.COURTSHIP_TOGETHER_SECONDS / 0.5) + 2
        for _ in range(ticks_needed):
            controller._update_current_behavior(male, 0.5)

        assert len(controller.completed_courtships) == 1
        assert controller.completed_courtships[0] == (male.id, female.id)


class TestCourtshipInterruption:
    """Tests for courtship being interrupted."""

    def test_critical_hunger_interrupts_courtship(self):
        state = GameState()
        male, female = _make_breedable_pair(state)

        _initiate_courtship(male, female, state)
        male.needs.hunger = 5.0  # Critical

        controller = BehaviorController(state)
        controller.collision.rebuild_spatial_grid()
        make_decision(controller,male)

        assert male.behavior_state != BehaviorState.COURTING
        assert female.behavior_state != BehaviorState.COURTING
        assert male.courting_partner_id is None
        assert female.courting_partner_id is None

    def test_critical_thirst_interrupts_courtship(self):
        state = GameState()
        male, female = _make_breedable_pair(state)

        _initiate_courtship(male, female, state)
        male.needs.thirst = 5.0  # Critical

        controller = BehaviorController(state)
        controller.collision.rebuild_spatial_grid()
        make_decision(controller,male)

        assert male.behavior_state != BehaviorState.COURTING
        assert female.behavior_state != BehaviorState.COURTING

    def test_partner_removal_cancels_courtship(self):
        state = GameState()
        male, female = _make_breedable_pair(state)

        _initiate_courtship(male, female, state)

        controller = BehaviorController(state)
        state.remove_guinea_pig(female.id)
        controller.cleanup_dead_pig(female.id)

        assert male.behavior_state != BehaviorState.COURTING
        assert male.courting_partner_id is None

    def test_partner_no_longer_courting_cancels(self):
        state = GameState()
        male, female = _make_breedable_pair(state)

        _initiate_courtship(male, female, state)
        # Externally force female out of courting (simulating some other interruption)
        female.behavior_state = BehaviorState.IDLE

        controller = BehaviorController(state)
        controller.collision.rebuild_spatial_grid()
        make_decision(controller,male)

        assert male.behavior_state != BehaviorState.COURTING
        assert male.courting_partner_id is None


class TestClearCourtship:
    """Tests for clear_courtship helper."""

    def test_clear_courtship_resets_all_fields(self):
        pig = _make_pig("Test", Gender.MALE)
        pig.behavior_state = BehaviorState.COURTING
        pig.courting_partner_id = uuid4()
        pig.courting_initiator = True
        pig.courting_timer = 3.5

        clear_courtship(pig)

        assert pig.courting_partner_id is None
        assert pig.courting_initiator is False
        assert pig.courting_timer == 0.0
        assert pig.behavior_state == BehaviorState.IDLE
        assert pig.target_description is None

    def test_clear_courtship_preserves_non_courting_state(self):
        pig = _make_pig("Test", Gender.MALE)
        pig.behavior_state = BehaviorState.EATING
        pig.courting_partner_id = uuid4()

        clear_courtship(pig)

        # Should not change behavior state since it wasn't COURTING
        assert pig.behavior_state == BehaviorState.EATING


class TestSocialAffinity:
    """Tests for the social affinity system."""

    def test_affinity_starts_at_zero(self):
        state = GameState()
        id1, id2 = uuid4(), uuid4()
        assert state.get_affinity(id1, id2) == 0

    def test_increment_affinity(self):
        state = GameState()
        id1, id2 = uuid4(), uuid4()

        state.increment_affinity(id1, id2)
        assert state.get_affinity(id1, id2) == 1

        state.increment_affinity(id1, id2)
        assert state.get_affinity(id1, id2) == 2

    def test_affinity_symmetric(self):
        state = GameState()
        id1, id2 = uuid4(), uuid4()

        state.increment_affinity(id1, id2)
        assert state.get_affinity(id2, id1) == 1

    def test_affinity_cleaned_on_pig_removal(self):
        state = GameState()
        pig1 = _make_pig("A", Gender.MALE, x=5.0, y=5.0)
        pig2 = _make_pig("B", Gender.FEMALE, x=6.0, y=5.0)
        state.add_guinea_pig(pig1)
        state.add_guinea_pig(pig2)

        state.increment_affinity(pig1.id, pig2.id)
        assert state.get_affinity(pig1.id, pig2.id) == 1

        state.remove_guinea_pig(pig1.id)
        assert state.get_affinity(pig1.id, pig2.id) == 0
        assert len(state.social_affinity) == 0

    def test_affinity_increments_on_socialization_completion(self):
        state = GameState()
        pig1 = _make_pig("Social1", Gender.MALE, x=5.0, y=5.0)
        pig2 = _make_pig("Social2", Gender.FEMALE, x=6.0, y=5.0)
        pig1.needs.social = 95  # Will trigger "finished socializing" path
        pig2.needs.social = 50
        pig1.behavior_state = BehaviorState.SOCIALIZING
        pig2.behavior_state = BehaviorState.SOCIALIZING
        state.add_guinea_pig(pig1)
        state.add_guinea_pig(pig2)

        controller = BehaviorController(state)
        controller.collision.rebuild_spatial_grid()
        # Affinity only increments from the pig with smaller UUID (dedup guard)
        finisher = pig1 if pig1.id < pig2.id else pig2
        finisher.needs.social = 95
        make_decision(controller,finisher)

        assert state.get_affinity(pig1.id, pig2.id) >= 1

    def test_affinity_biases_auto_pair(self):
        from big_pig_farm.entities.genetics import Genotype

        state = GameState()
        # Use identical explicit genotypes so probability is equal for both males
        geno = Genotype(
            e_locus=("E", "E"), b_locus=("B", "B"),
            s_locus=("S", "S"), c_locus=("C", "C"), r_locus=("r", "r"),
        )
        male1 = _make_pig("M1", Gender.MALE, age_days=5.0, x=5.0, y=5.0, genotype=geno)
        male2 = _make_pig("M2", Gender.MALE, age_days=5.0, x=10.0, y=5.0, genotype=geno)
        female = _make_pig("F1", Gender.FEMALE, age_days=5.0, x=15.0, y=5.0, genotype=geno)
        for pig in [male1, male2, female]:
            pig.needs.happiness = 90
            pig.needs.health = 100
            pig.breeding_locked = False
            state.add_guinea_pig(pig)

        # Give male2 high affinity with female
        for _ in range(20):
            state.increment_affinity(male2.id, female.id)

        # Enable breeding program with a target
        state.breeding_program = BreedingProgram(
            enabled=True, auto_pair=True, target_colors={BaseColor.BLACK},
        )

        check_breeding_opportunities(state)

        # Both males have identical genotypes so probability is equal
        # — affinity tips the scale toward male2
        if state.breeding_pair:
            assert state.breeding_pair.male_id == male2.id
