"""Tests for the breeding program system."""

import pytest

from big_pig_farm.entities.guinea_pig import GuineaPig, Gender, Position
from big_pig_farm.entities.genetics import (
    Genotype,
    BaseColor,
    Pattern,
    ColorIntensity,
    RoanType,
    calculate_phenotype,
    calculate_target_probability,
)
from big_pig_farm.data.config import BREEDING
from big_pig_farm.simulation.breeding_program import (
    BreedingProgram, should_keep_pig, breeding_value, diversity_value, _heterozygosity_count,
)
from big_pig_farm.simulation.breeding import (
    _auto_pair_from_program, _apply_breeding_filter, cull_surplus_breeders,
    _would_break_gender_balance,
)
from big_pig_farm.game.state import GameState


def _make_pig_with_genotype(**loci) -> GuineaPig:
    """Create a pig with specific locus values.

    Pass keyword args like e_locus=("E", "e"), b_locus=("b", "b"), etc.
    Unspecified loci default to homozygous dominant.
    """
    defaults = {
        "e_locus": ("E", "E"),
        "b_locus": ("B", "B"),
        "s_locus": ("S", "S"),
        "c_locus": ("C", "C"),
        "r_locus": ("r", "r"),
    }
    defaults.update(loci)
    genotype = Genotype(**defaults)
    return GuineaPig.create(
        name="Test",
        gender=Gender.MALE,
        genotype=genotype,
        position=Position(x=5.0, y=5.0),
    )


def _make_pig(name: str, gender: Gender, age_days: float = 5.0, **loci) -> GuineaPig:
    """Create a named pig with specific locus values and gender."""
    defaults = {
        "e_locus": ("E", "E"),
        "b_locus": ("B", "B"),
        "s_locus": ("S", "S"),
        "c_locus": ("C", "C"),
        "r_locus": ("r", "r"),
    }
    defaults.update(loci)
    genotype = Genotype(**defaults)
    return GuineaPig.create(
        name=name,
        gender=gender,
        genotype=genotype,
        position=Position(x=5.0, y=5.0),
        age_days=age_days,
    )


# ─── should_keep_pig tests (migrated from old test_breeding_filter.py) ───


class TestDisabledProgram:
    """A disabled program should keep everything."""

    def test_disabled_keeps_all(self):
        f = BreedingProgram(enabled=False, target_colors={BaseColor.CHOCOLATE})
        pig = _make_pig_with_genotype()  # Black, Solid, Full, no Roan
        assert should_keep_pig(f, pig, has_genetics_lab=False)

    def test_default_program_keeps_all(self):
        f = BreedingProgram()
        pig = _make_pig_with_genotype()
        assert should_keep_pig(f, pig, has_genetics_lab=False)


class TestEmptyAxes:
    """Empty set on an axis means 'don't filter that axis'."""

    def test_empty_program_enabled_keeps_all(self):
        f = BreedingProgram(enabled=True)
        pig = _make_pig_with_genotype()
        assert should_keep_pig(f, pig, has_genetics_lab=False)

    def test_empty_colors_keeps_any_color(self):
        f = BreedingProgram(enabled=True, target_patterns={Pattern.SOLID})
        pig = _make_pig_with_genotype(e_locus=("E", "E"), b_locus=("b", "b"))
        assert should_keep_pig(f, pig, has_genetics_lab=False)


class TestSingleAxisFiltering:
    """Test filtering on individual axes."""

    def test_color_match_keeps(self):
        f = BreedingProgram(enabled=True, target_colors={BaseColor.CHOCOLATE})
        pig = _make_pig_with_genotype(b_locus=("b", "b"))
        assert should_keep_pig(f, pig, has_genetics_lab=False)

    def test_color_mismatch_marks(self):
        f = BreedingProgram(enabled=True, target_colors={BaseColor.CHOCOLATE})
        pig = _make_pig_with_genotype()
        assert not should_keep_pig(f, pig, has_genetics_lab=False)

    def test_multiple_colors_or_logic(self):
        f = BreedingProgram(enabled=True, target_colors={BaseColor.CHOCOLATE, BaseColor.GOLDEN})
        black_pig = _make_pig_with_genotype()
        choc_pig = _make_pig_with_genotype(b_locus=("b", "b"))
        golden_pig = _make_pig_with_genotype(e_locus=("e", "e"))
        assert not should_keep_pig(f, black_pig, has_genetics_lab=False)
        assert should_keep_pig(f, choc_pig, has_genetics_lab=False)
        assert should_keep_pig(f, golden_pig, has_genetics_lab=False)

    def test_pattern_match_keeps(self):
        f = BreedingProgram(enabled=True, target_patterns={Pattern.DALMATIAN})
        pig = _make_pig_with_genotype(s_locus=("s", "s"))
        assert should_keep_pig(f, pig, has_genetics_lab=False)

    def test_pattern_mismatch_marks(self):
        f = BreedingProgram(enabled=True, target_patterns={Pattern.DALMATIAN})
        pig = _make_pig_with_genotype(s_locus=("S", "S"))
        assert not should_keep_pig(f, pig, has_genetics_lab=False)

    def test_intensity_match_keeps(self):
        f = BreedingProgram(enabled=True, target_intensities={ColorIntensity.HIMALAYAN})
        pig = _make_pig_with_genotype(c_locus=("ch", "ch"))
        assert should_keep_pig(f, pig, has_genetics_lab=False)

    def test_intensity_mismatch_marks(self):
        f = BreedingProgram(enabled=True, target_intensities={ColorIntensity.HIMALAYAN})
        pig = _make_pig_with_genotype(c_locus=("C", "C"))
        assert not should_keep_pig(f, pig, has_genetics_lab=False)

    def test_roan_match_keeps(self):
        f = BreedingProgram(enabled=True, target_roan={RoanType.ROAN})
        pig = _make_pig_with_genotype(r_locus=("R", "r"))
        assert should_keep_pig(f, pig, has_genetics_lab=False)

    def test_roan_mismatch_marks(self):
        f = BreedingProgram(enabled=True, target_roan={RoanType.ROAN})
        pig = _make_pig_with_genotype(r_locus=("r", "r"))
        assert not should_keep_pig(f, pig, has_genetics_lab=False)


class TestMultiAxisAndLogic:
    """Multiple axes must ALL match (AND logic)."""

    def test_two_axes_both_match(self):
        f = BreedingProgram(
            enabled=True,
            target_colors={BaseColor.CHOCOLATE},
            target_patterns={Pattern.DALMATIAN},
        )
        pig = _make_pig_with_genotype(b_locus=("b", "b"), s_locus=("s", "s"))
        assert should_keep_pig(f, pig, has_genetics_lab=False)

    def test_two_axes_one_fails(self):
        f = BreedingProgram(
            enabled=True,
            target_colors={BaseColor.CHOCOLATE},
            target_patterns={Pattern.DALMATIAN},
        )
        pig = _make_pig_with_genotype(b_locus=("b", "b"), s_locus=("S", "S"))
        assert not should_keep_pig(f, pig, has_genetics_lab=False)

    def test_all_four_axes(self):
        f = BreedingProgram(
            enabled=True,
            target_colors={BaseColor.GOLDEN},
            target_patterns={Pattern.DUTCH},
            target_intensities={ColorIntensity.HIMALAYAN},
            target_roan={RoanType.ROAN},
        )
        pig = _make_pig_with_genotype(
            e_locus=("e", "e"),
            b_locus=("B", "B"),
            s_locus=("S", "s"),
            c_locus=("ch", "ch"),
            r_locus=("R", "r"),
        )
        assert should_keep_pig(f, pig, has_genetics_lab=False)


class TestCarrierAware:
    """Keep-carriers mode rescues heterozygous pigs when Genetics Lab exists."""

    def test_keep_carriers_requires_genetics_lab(self):
        f = BreedingProgram(
            enabled=True,
            target_colors={BaseColor.CHOCOLATE},
            keep_carriers=True,
        )
        pig = _make_pig_with_genotype(b_locus=("B", "b"))
        assert not should_keep_pig(f, pig, has_genetics_lab=False)

    def test_keep_carriers_with_lab_keeps_carrier(self):
        f = BreedingProgram(
            enabled=True,
            target_colors={BaseColor.CHOCOLATE},
            keep_carriers=True,
        )
        pig = _make_pig_with_genotype(b_locus=("B", "b"))
        assert should_keep_pig(f, pig, has_genetics_lab=True)

    def test_keep_carriers_golden(self):
        f = BreedingProgram(
            enabled=True,
            target_colors={BaseColor.GOLDEN},
            keep_carriers=True,
        )
        pig = _make_pig_with_genotype(e_locus=("E", "e"))
        assert should_keep_pig(f, pig, has_genetics_lab=True)

    def test_keep_carriers_cream(self):
        f = BreedingProgram(
            enabled=True,
            target_colors={BaseColor.CREAM},
            keep_carriers=True,
        )
        pig = _make_pig_with_genotype(e_locus=("E", "e"), b_locus=("B", "b"))
        assert should_keep_pig(f, pig, has_genetics_lab=True)

    def test_keep_carriers_cream_needs_both_alleles(self):
        f = BreedingProgram(
            enabled=True,
            target_colors={BaseColor.CREAM},
            keep_carriers=True,
        )
        pig = _make_pig_with_genotype(e_locus=("E", "e"), b_locus=("B", "B"))
        assert not should_keep_pig(f, pig, has_genetics_lab=True)

    def test_keep_carriers_pattern_dutch(self):
        f = BreedingProgram(
            enabled=True,
            target_patterns={Pattern.DUTCH},
            keep_carriers=True,
        )
        pig = _make_pig_with_genotype(s_locus=("S", "S"))
        assert not should_keep_pig(f, pig, has_genetics_lab=True)

    def test_keep_carriers_pattern_dalmatian_rescued(self):
        f = BreedingProgram(
            enabled=True,
            target_patterns={Pattern.DALMATIAN},
            keep_carriers=True,
        )
        pig = _make_pig_with_genotype(s_locus=("S", "s"))
        assert should_keep_pig(f, pig, has_genetics_lab=True)

    def test_keep_carriers_intensity_himalayan(self):
        f = BreedingProgram(
            enabled=True,
            target_intensities={ColorIntensity.HIMALAYAN},
            keep_carriers=True,
        )
        pig = _make_pig_with_genotype(c_locus=("C", "ch"))
        assert should_keep_pig(f, pig, has_genetics_lab=True)

    def test_keep_carriers_no_rescue_for_dominant_traits(self):
        f = BreedingProgram(
            enabled=True,
            target_colors={BaseColor.BLACK},
            keep_carriers=True,
        )
        pig = _make_pig_with_genotype(e_locus=("E", "E"), b_locus=("b", "b"))
        assert not should_keep_pig(f, pig, has_genetics_lab=True)

    def test_keep_carriers_roan_no_rescue(self):
        f = BreedingProgram(
            enabled=True,
            target_roan={RoanType.ROAN},
            keep_carriers=True,
        )
        pig = _make_pig_with_genotype(r_locus=("r", "r"))
        assert not should_keep_pig(f, pig, has_genetics_lab=True)


# ─── calculate_target_probability tests ───


class TestTargetProbability:
    """Tests for analytical target probability calculation."""

    def test_carriers_ee_cross_golden(self):
        """Ee x Ee -> P(ee) = 25% for golden."""
        p1 = Genotype(e_locus=("E", "e"), b_locus=("B", "B"), s_locus=("S", "S"), c_locus=("C", "C"), r_locus=("r", "r"))
        p2 = Genotype(e_locus=("E", "e"), b_locus=("B", "B"), s_locus=("S", "S"), c_locus=("C", "C"), r_locus=("r", "r"))
        prob = calculate_target_probability(p1, p2, {BaseColor.GOLDEN}, set(), set(), set())
        assert abs(prob - 0.25) < 0.001

    def test_homozygous_match_100(self):
        """ee x ee -> P(ee) = 100% for golden."""
        p1 = Genotype(e_locus=("e", "e"), b_locus=("B", "B"), s_locus=("S", "S"), c_locus=("C", "C"), r_locus=("r", "r"))
        p2 = Genotype(e_locus=("e", "e"), b_locus=("B", "B"), s_locus=("S", "S"), c_locus=("C", "C"), r_locus=("r", "r"))
        prob = calculate_target_probability(p1, p2, {BaseColor.GOLDEN}, set(), set(), set())
        assert abs(prob - 1.0) < 0.001

    def test_no_carrier_0(self):
        """EE x EE -> P(ee) = 0% for golden."""
        p1 = Genotype(e_locus=("E", "E"), b_locus=("B", "B"), s_locus=("S", "S"), c_locus=("C", "C"), r_locus=("r", "r"))
        p2 = Genotype(e_locus=("E", "E"), b_locus=("B", "B"), s_locus=("S", "S"), c_locus=("C", "C"), r_locus=("r", "r"))
        prob = calculate_target_probability(p1, p2, {BaseColor.GOLDEN}, set(), set(), set())
        assert prob == 0.0

    def test_partial_target_only_pattern(self):
        """Only pattern specified, no color -> only pattern probability matters."""
        # Ss x Ss -> P(ss) = 25% for Dalmatian
        p1 = Genotype(e_locus=("E", "E"), b_locus=("B", "B"), s_locus=("S", "s"), c_locus=("C", "C"), r_locus=("r", "r"))
        p2 = Genotype(e_locus=("E", "E"), b_locus=("B", "B"), s_locus=("S", "s"), c_locus=("C", "C"), r_locus=("r", "r"))
        prob = calculate_target_probability(p1, p2, set(), {Pattern.DALMATIAN}, set(), set())
        assert abs(prob - 0.25) < 0.001

    def test_multi_trait_product(self):
        """Multi-trait target = product of independent probabilities."""
        # Ee x Ee -> P(ee) = 25% for golden
        # Ss x Ss -> P(ss) = 25% for dalmatian
        # Both: 0.25 * 0.25 = 6.25%
        p1 = Genotype(e_locus=("E", "e"), b_locus=("B", "B"), s_locus=("S", "s"), c_locus=("C", "C"), r_locus=("r", "r"))
        p2 = Genotype(e_locus=("E", "e"), b_locus=("B", "B"), s_locus=("S", "s"), c_locus=("C", "C"), r_locus=("r", "r"))
        prob = calculate_target_probability(p1, p2, {BaseColor.GOLDEN}, {Pattern.DALMATIAN}, set(), set())
        assert abs(prob - 0.0625) < 0.001

    def test_empty_target_returns_1(self):
        """No target on any axis -> 100%."""
        p1 = Genotype(e_locus=("E", "E"), b_locus=("B", "B"), s_locus=("S", "S"), c_locus=("C", "C"), r_locus=("r", "r"))
        p2 = Genotype(e_locus=("E", "E"), b_locus=("B", "B"), s_locus=("S", "S"), c_locus=("C", "C"), r_locus=("r", "r"))
        prob = calculate_target_probability(p1, p2, set(), set(), set(), set())
        assert prob == 1.0

    def test_roan_lethal_redistribution(self):
        """Rr x Rr -> P(Rr or RR rerolled) should redistribute lethal RR."""
        # Rr x Rr: 25% RR (lethal), 50% Rr, 25% rr
        # After redistribution: Rr = 50/75 = 66.7%, rr = 25/75 = 33.3%
        p1 = Genotype(e_locus=("E", "E"), b_locus=("B", "B"), s_locus=("S", "S"), c_locus=("C", "C"), r_locus=("R", "r"))
        p2 = Genotype(e_locus=("E", "E"), b_locus=("B", "B"), s_locus=("S", "S"), c_locus=("C", "C"), r_locus=("R", "r"))
        prob_roan = calculate_target_probability(p1, p2, set(), set(), set(), {RoanType.ROAN})
        prob_none = calculate_target_probability(p1, p2, set(), set(), set(), {RoanType.NONE})
        assert abs(prob_roan - 2 / 3) < 0.001
        assert abs(prob_none - 1 / 3) < 0.001
        assert abs(prob_roan + prob_none - 1.0) < 0.001

    def test_intensity_himalayan(self):
        """C/ch x C/ch -> P(ch/ch) = 25% for himalayan."""
        p1 = Genotype(e_locus=("E", "E"), b_locus=("B", "B"), s_locus=("S", "S"), c_locus=("C", "ch"), r_locus=("r", "r"))
        p2 = Genotype(e_locus=("E", "E"), b_locus=("B", "B"), s_locus=("S", "S"), c_locus=("C", "ch"), r_locus=("r", "r"))
        prob = calculate_target_probability(p1, p2, set(), set(), {ColorIntensity.HIMALAYAN}, set())
        assert abs(prob - 0.25) < 0.001

    def test_multiple_colors_in_target(self):
        """Target {GOLDEN, CREAM} from Ee x Ee, Bb x Bb."""
        # P(ee) = 25%: of those, P(has_B) = 75% -> golden; P(bb) = 25% -> cream
        # P(golden) = 0.25 * 0.75 = 18.75%, P(cream) = 0.25 * 0.25 = 6.25%
        # Total = 25%
        p1 = Genotype(e_locus=("E", "e"), b_locus=("B", "b"), s_locus=("S", "S"), c_locus=("C", "C"), r_locus=("r", "r"))
        p2 = Genotype(e_locus=("E", "e"), b_locus=("B", "b"), s_locus=("S", "S"), c_locus=("C", "C"), r_locus=("r", "r"))
        prob = calculate_target_probability(p1, p2, {BaseColor.GOLDEN, BaseColor.CREAM}, set(), set(), set())
        assert abs(prob - 0.25) < 0.001


# ─── _auto_pair_from_program tests ───


class TestAutoPair:
    """Tests for auto-pairing logic."""

    def test_picks_best_pair(self):
        """Auto-pair should select the pair with highest target probability."""
        state = GameState()
        # Male 1: EE (no golden alleles)
        male1 = _make_pig("M1", Gender.MALE, e_locus=("E", "E"))
        # Male 2: ee (homozygous golden)
        male2 = _make_pig("M2", Gender.MALE, e_locus=("e", "e"))
        # Female: Ee (carrier)
        female = _make_pig("F1", Gender.FEMALE, e_locus=("E", "e"))

        state.add_guinea_pig(male1)
        state.add_guinea_pig(male2)
        state.add_guinea_pig(female)

        state.breeding_program = BreedingProgram(
            enabled=True,
            auto_pair=True,
            target_colors={BaseColor.GOLDEN},
        )

        _auto_pair_from_program(state)

        # Should pick male2 x female (higher golden probability)
        assert state.breeding_pair is not None
        assert state.breeding_pair.male_id == male2.id
        assert state.breeding_pair.female_id == female.id

    def test_skips_breeding_locked_pigs(self):
        """Auto-pair should skip breeding-locked pigs."""
        state = GameState()
        male = _make_pig("M1", Gender.MALE, e_locus=("e", "e"))
        male.breeding_locked = True
        female = _make_pig("F1", Gender.FEMALE, e_locus=("e", "e"))

        state.add_guinea_pig(male)
        state.add_guinea_pig(female)

        state.breeding_program = BreedingProgram(
            enabled=True,
            auto_pair=True,
            target_colors={BaseColor.GOLDEN},
        )

        _auto_pair_from_program(state)
        assert state.breeding_pair is None

    def test_skips_when_disabled(self):
        """Auto-pair does nothing when program is disabled."""
        state = GameState()
        male = _make_pig("M1", Gender.MALE, e_locus=("e", "e"))
        female = _make_pig("F1", Gender.FEMALE, e_locus=("e", "e"))

        state.add_guinea_pig(male)
        state.add_guinea_pig(female)

        state.breeding_program = BreedingProgram(
            enabled=False,
            auto_pair=True,
            target_colors={BaseColor.GOLDEN},
        )

        _auto_pair_from_program(state)
        assert state.breeding_pair is None

    def test_does_not_override_manual_pair(self):
        """Auto-pair should not override an existing manual breeding pair."""
        state = GameState()
        male = _make_pig("M1", Gender.MALE, e_locus=("e", "e"))
        female = _make_pig("F1", Gender.FEMALE, e_locus=("e", "e"))

        state.add_guinea_pig(male)
        state.add_guinea_pig(female)

        # Set a manual pair first
        state.set_breeding_pair(male.id, female.id)

        state.breeding_program = BreedingProgram(
            enabled=True,
            auto_pair=True,
            target_colors={BaseColor.GOLDEN},
        )

        _auto_pair_from_program(state)
        # Should still be the original pair
        assert state.breeding_pair.male_id == male.id
        assert state.breeding_pair.female_id == female.id

    def test_skips_when_no_target(self):
        """Auto-pair does nothing when no target traits are set."""
        state = GameState()
        male = _make_pig("M1", Gender.MALE)
        female = _make_pig("F1", Gender.FEMALE)

        state.add_guinea_pig(male)
        state.add_guinea_pig(female)

        state.breeding_program = BreedingProgram(
            enabled=True,
            auto_pair=True,
        )

        _auto_pair_from_program(state)
        assert state.breeding_pair is None


# ─── cull_surplus_breeders tests ───


class TestCullSurplus:
    """Tests for surplus culling logic."""

    def test_under_limit_no_culling(self):
        """No culling when under stock limit."""
        state = GameState()
        for i in range(4):
            gender = Gender.MALE if i % 2 == 0 else Gender.FEMALE
            pig = _make_pig(f"Pig{i}", gender)
            state.add_guinea_pig(pig)

        state.breeding_program = BreedingProgram(enabled=True, stock_limit=6)

        cull_surplus_breeders(state)
        assert all(not p.marked_for_sale for p in state.get_pigs_list())

    def test_over_limit_marks_lowest_value(self):
        """Over stock limit should mark lowest-value pigs."""
        state = GameState()
        # Create 7 adults: 4 with golden alleles (higher value), 3 without
        # Need > MIN_BREEDING_POPULATION + surplus to test properly
        for i in range(4):
            gender = Gender.MALE if i == 0 else Gender.FEMALE
            pig = _make_pig(f"Good{i}", gender, e_locus=("e", "e"))
            state.add_guinea_pig(pig)
        for i in range(3):
            gender = Gender.MALE if i == 0 else Gender.FEMALE
            pig = _make_pig(f"Bad{i}", gender, e_locus=("E", "E"))
            state.add_guinea_pig(pig)

        state.breeding_program = BreedingProgram(
            enabled=True,
            stock_limit=4,
            target_colors={BaseColor.GOLDEN},
        )

        cull_surplus_breeders(state)
        marked = [p for p in state.get_pigs_list() if p.marked_for_sale]
        assert len(marked) == 3
        # The marked ones should be the "Bad" pigs (no golden alleles)
        assert all("Bad" in p.name for p in marked)

    def test_gender_balance_preserved(self):
        """Should keep at least 1 male and 1 female."""
        state = GameState()
        # All females except one male, all with same genetics
        male = _make_pig("OnlyMale", Gender.MALE, e_locus=("e", "e"))
        state.add_guinea_pig(male)
        for i in range(5):
            pig = _make_pig(f"F{i}", Gender.FEMALE, e_locus=("e", "e"))
            state.add_guinea_pig(pig)

        state.breeding_program = BreedingProgram(
            enabled=True,
            stock_limit=3,
            target_colors={BaseColor.GOLDEN},
        )

        cull_surplus_breeders(state)
        kept = [p for p in state.get_pigs_list() if not p.marked_for_sale]
        kept_males = [p for p in kept if p.gender == Gender.MALE]
        kept_females = [p for p in kept if p.gender == Gender.FEMALE]
        assert len(kept_males) >= 1
        assert len(kept_females) >= 1

    def test_pregnant_pigs_not_marked(self):
        """Pregnant pigs should not be marked for sale."""
        state = GameState()
        male = _make_pig("M1", Gender.MALE)
        state.add_guinea_pig(male)
        for i in range(4):
            pig = _make_pig(f"F{i}", Gender.FEMALE)
            if i == 0:
                pig.is_pregnant = True
            state.add_guinea_pig(pig)

        state.breeding_program = BreedingProgram(enabled=True, stock_limit=2)

        cull_surplus_breeders(state)
        pregnant = [p for p in state.get_pigs_list() if p.is_pregnant]
        assert all(not p.marked_for_sale for p in pregnant)

    def test_disabled_program_no_culling(self):
        """No culling when program is disabled."""
        state = GameState()
        for i in range(10):
            gender = Gender.MALE if i % 2 == 0 else Gender.FEMALE
            pig = _make_pig(f"Pig{i}", gender)
            state.add_guinea_pig(pig)

        state.breeding_program = BreedingProgram(enabled=False, stock_limit=3)

        cull_surplus_breeders(state)
        assert all(not p.marked_for_sale for p in state.get_pigs_list())


# ─── has_target and breeding_value tests ───


class TestBreedingProgramModel:
    """Tests for BreedingProgram model properties."""

    def test_has_target_empty(self):
        bp = BreedingProgram()
        assert not bp.has_target

    def test_has_target_with_color(self):
        bp = BreedingProgram(target_colors={BaseColor.GOLDEN})
        assert bp.has_target

    def test_should_auto_pair_disabled(self):
        bp = BreedingProgram(enabled=False, auto_pair=True)
        assert not bp.should_auto_pair()

    def test_should_auto_pair_enabled(self):
        bp = BreedingProgram(enabled=True, auto_pair=True)
        assert bp.should_auto_pair()

    def test_breeding_value_golden_target(self):
        """Pig with ee should score higher than EE for golden target."""
        program = BreedingProgram(target_colors={BaseColor.GOLDEN})
        pig_ee = _make_pig_with_genotype(e_locus=("e", "e"))
        pig_EE = _make_pig_with_genotype(e_locus=("E", "E"))
        assert breeding_value(pig_ee, program, False) > breeding_value(pig_EE, program, False)


# ─── Age-aware breeding value tests ───


class TestBreedingValueAge:
    """Tests for the age tiebreaker in breeding_value()."""

    def test_younger_pig_scores_higher_than_older(self):
        """Young adult should score higher than older adult with same genetics."""
        program = BreedingProgram(target_colors={BaseColor.GOLDEN})
        young = _make_pig("Young", Gender.MALE, age_days=5.0, e_locus=("e", "e"))
        old = _make_pig("Old", Gender.MALE, age_days=25.0, e_locus=("e", "e"))
        assert breeding_value(young, program, False) > breeding_value(old, program, False)

    def test_senior_scores_lower_than_adult(self):
        """Senior pig should score lower than adult with same genetics."""
        program = BreedingProgram(target_colors={BaseColor.GOLDEN})
        adult = _make_pig("Adult", Gender.MALE, age_days=10.0, e_locus=("e", "e"))
        senior = _make_pig("Senior", Gender.MALE, age_days=35.0, e_locus=("e", "e"))
        assert breeding_value(adult, program, False) > breeding_value(senior, program, False)

    def test_good_genetics_beats_age_advantage(self):
        """Pig with much better genetics should still beat a younger pig with no target alleles."""
        program = BreedingProgram(
            target_colors={BaseColor.GOLDEN},
            target_patterns={Pattern.DALMATIAN},
            target_roan={RoanType.ROAN},
        )
        # Score: e(2) + s(2) + R(1) = 5 alleles + small age bonus
        old_good = _make_pig(
            "OldGood", Gender.MALE, age_days=25.0,
            e_locus=("e", "e"), s_locus=("s", "s"), r_locus=("R", "r"),
        )
        # Score: 0 alleles + large age bonus (~4.2)
        young_bad = _make_pig("YoungBad", Gender.MALE, age_days=5.0)
        assert breeding_value(old_good, program, False) > breeding_value(young_bad, program, False)

    def test_senior_always_below_breeder(self):
        """A senior with perfect genetics should still score below any breeding-age pig."""
        program = BreedingProgram(
            target_colors={BaseColor.GOLDEN},
            target_patterns={Pattern.DALMATIAN},
            target_intensities={ColorIntensity.HIMALAYAN},
            target_roan={RoanType.ROAN},
        )
        # Senior with max alleles on every axis
        senior = _make_pig(
            "Senior", Gender.MALE, age_days=35.0,
            e_locus=("e", "e"), s_locus=("s", "s"), c_locus=("ch", "ch"), r_locus=("R", "r"),
        )
        # Young pig with zero target alleles
        young = _make_pig("Young", Gender.MALE, age_days=5.0)
        assert breeding_value(young, program, False) > breeding_value(senior, program, False)

    def test_senior_diversity_below_breeder(self):
        """A senior should score below a breeding-age pig in diversity mode too."""
        senior = _make_pig("Senior", Gender.MALE, age_days=35.0, e_locus=("E", "e"), b_locus=("B", "b"))
        young = _make_pig("Young", Gender.MALE, age_days=5.0)
        all_pigs = [senior, young]
        assert diversity_value(young, all_pigs) > diversity_value(senior, all_pigs)


# ─── Culling with population floor tests ───


class TestCullPopulationFloor:
    """Tests for the MIN_BREEDING_POPULATION floor in culling."""

    def test_cull_at_min_population_uses_active_replacement(self):
        """At MIN_BREEDING_POPULATION, surplus culling doesn't fire but active replacement does."""
        state = GameState()
        # Create exactly MIN_BREEDING_POPULATION adults (all non-matching)
        for i in range(BREEDING.MIN_BREEDING_POPULATION):
            gender = Gender.MALE if i == 0 else Gender.FEMALE
            pig = _make_pig(f"Pig{i}", gender)
            state.add_guinea_pig(pig)

        # stock_limit=2 is below MIN_BREEDING_POPULATION
        state.breeding_program = BreedingProgram(
            enabled=True,
            stock_limit=2,
            target_colors={BaseColor.GOLDEN},
        )

        cull_surplus_breeders(state)
        # Active replacement marks exactly 1 non-matching pig
        marked = [p for p in state.get_pigs_list() if p.marked_for_sale]
        assert len(marked) == 1

    def test_cull_sells_seniors_first(self):
        """Should sell seniors before young adults with equal genetics."""
        state = GameState()
        # 6 adults: 3 young + 3 senior, all same genetics
        for i in range(3):
            gender = Gender.MALE if i == 0 else Gender.FEMALE
            pig = _make_pig(f"Young{i}", gender, age_days=5.0, e_locus=("e", "e"))
            state.add_guinea_pig(pig)
        for i in range(3):
            gender = Gender.MALE if i == 0 else Gender.FEMALE
            pig = _make_pig(f"Senior{i}", gender, age_days=35.0, e_locus=("e", "e"))
            state.add_guinea_pig(pig)

        state.breeding_program = BreedingProgram(
            enabled=True,
            stock_limit=4,
            target_colors={BaseColor.GOLDEN},
        )

        cull_surplus_breeders(state)
        marked = [p for p in state.get_pigs_list() if p.marked_for_sale]
        assert len(marked) == 2
        # Marked pigs should be the seniors (lower breeding value due to age)
        assert all("Senior" in p.name for p in marked)

    def test_filter_skips_when_population_low(self):
        """_apply_breeding_filter should skip marking when adults <= MIN_BREEDING_POPULATION."""
        state = GameState()
        # Create adults at the floor
        for i in range(BREEDING.MIN_BREEDING_POPULATION):
            gender = Gender.MALE if i == 0 else Gender.FEMALE
            pig = _make_pig(f"Adult{i}", gender)
            state.add_guinea_pig(pig)

        state.breeding_program = BreedingProgram(
            enabled=True,
            target_colors={BaseColor.GOLDEN},
        )

        # Create a baby that doesn't match the target
        baby = _make_pig("Baby", Gender.MALE, age_days=0.0, e_locus=("E", "E"))
        state.add_guinea_pig(baby)

        _apply_breeding_filter(state, [baby])
        # Baby should NOT be marked because population is at the floor
        assert not baby.marked_for_sale


# ─── Diversity scoring tests ───


class TestHeterozygosityCount:
    """Tests for _heterozygosity_count helper."""

    def test_fully_homozygous_is_zero(self):
        g = Genotype(e_locus=("E", "E"), b_locus=("B", "B"), s_locus=("S", "S"), c_locus=("C", "C"), r_locus=("r", "r"))
        assert _heterozygosity_count(g) == 0

    def test_fully_heterozygous_is_five(self):
        g = Genotype(e_locus=("E", "e"), b_locus=("B", "b"), s_locus=("S", "s"), c_locus=("C", "ch"), r_locus=("R", "r"))
        assert _heterozygosity_count(g) == 5

    def test_c_locus_detected(self):
        """C/ch heterozygosity should be detected despite multi-char allele."""
        g = Genotype(e_locus=("E", "E"), b_locus=("B", "B"), s_locus=("S", "S"), c_locus=("C", "ch"), r_locus=("r", "r"))
        assert _heterozygosity_count(g) == 1


class TestDiversityValue:
    """Tests for diversity_value scoring."""

    def test_unique_beats_duplicate(self):
        """A pig with a unique phenotype should score higher than a duplicate."""
        # 3 black pigs (duplicates) + 1 golden pig (unique)
        black1 = _make_pig("B1", Gender.MALE, age_days=5.0)
        black2 = _make_pig("B2", Gender.FEMALE, age_days=5.0)
        black3 = _make_pig("B3", Gender.FEMALE, age_days=5.0)
        golden = _make_pig("G1", Gender.MALE, age_days=5.0, e_locus=("e", "e"))
        all_pigs = [black1, black2, black3, golden]

        assert diversity_value(golden, all_pigs) > diversity_value(black1, all_pigs)

    def test_heterozygous_beats_homozygous(self):
        """A pig with more carrier alleles should score higher (same phenotype)."""
        # Both are black solid — same phenotype, different genotype depth
        homo = _make_pig("Homo", Gender.MALE, age_days=5.0,
                         e_locus=("E", "E"), b_locus=("B", "B"))
        het = _make_pig("Het", Gender.MALE, age_days=5.0,
                        e_locus=("E", "e"), b_locus=("B", "b"), s_locus=("S", "s"))
        all_pigs = [homo, het]

        assert diversity_value(het, all_pigs) > diversity_value(homo, all_pigs)


class TestCullWithDiversity:
    """Tests for culling with maximize_diversity enabled."""

    def test_keeps_unique_phenotypes(self):
        """With diversity mode, unique phenotypes should survive culling over duplicates."""
        state = GameState()
        # 4 Black pigs (same phenotype — duplicates)
        for i in range(4):
            gender = Gender.MALE if i == 0 else Gender.FEMALE
            pig = _make_pig(f"Black{i}", gender, age_days=5.0)
            state.add_guinea_pig(pig)
        # 1 Golden pig (unique phenotype)
        golden = _make_pig("Golden", Gender.FEMALE, age_days=5.0, e_locus=("e", "e"))
        state.add_guinea_pig(golden)
        # 1 Chocolate pig (unique phenotype)
        choc = _make_pig("Choc", Gender.MALE, age_days=5.0, b_locus=("b", "b"))
        state.add_guinea_pig(choc)

        # effective_limit = max(stock_limit, MIN_BREEDING_POPULATION) = 4
        state.breeding_program = BreedingProgram(
            enabled=True,
            maximize_diversity=True,
            stock_limit=3,
        )

        cull_surplus_breeders(state)
        kept = [p for p in state.get_pigs_list() if not p.marked_for_sale]
        kept_names = {p.name for p in kept}

        # Both unique phenotypes must survive
        assert "Golden" in kept_names
        assert "Choc" in kept_names
        # 2 of the 4 black pigs should be marked (surplus duplicates)
        marked = [p for p in state.get_pigs_list() if p.marked_for_sale]
        assert len(marked) == 2

    def test_diversity_culls_seniors_before_young(self):
        """Seniors should be culled before young pigs even in diversity mode."""
        state = GameState()
        # Senior with unique phenotype (golden)
        senior = _make_pig("SeniorGold", Gender.MALE, age_days=35.0, e_locus=("e", "e"))
        state.add_guinea_pig(senior)
        # Young pigs — all black (duplicates), but breeding-age
        for i in range(4):
            gender = Gender.MALE if i == 0 else Gender.FEMALE
            pig = _make_pig(f"Young{i}", gender, age_days=5.0)
            state.add_guinea_pig(pig)

        # effective_limit = max(3, MIN_BREEDING_POPULATION) = 4
        state.breeding_program = BreedingProgram(
            enabled=True,
            maximize_diversity=True,
            stock_limit=3,
        )

        cull_surplus_breeders(state)
        marked = [p for p in state.get_pigs_list() if p.marked_for_sale]
        marked_names = {p.name for p in marked}
        # Senior should be culled despite unique phenotype — can't breed
        assert "SeniorGold" in marked_names


# ─── Active replacement tests ───


class TestActiveReplacement:
    """Tests for the active replacement path in cull_surplus_breeders()."""

    def test_non_matching_marked_at_stock_limit(self):
        """A non-matching adult is marked for sale even when at stock limit."""
        state = GameState()
        # 2 matching + 2 non-matching = 4 adults at stock_limit=4
        state.add_guinea_pig(_make_pig("Good1", Gender.MALE, e_locus=("e", "e")))
        state.add_guinea_pig(_make_pig("Good2", Gender.FEMALE, e_locus=("e", "e")))
        state.add_guinea_pig(_make_pig("Bad1", Gender.MALE, e_locus=("E", "E")))
        state.add_guinea_pig(_make_pig("Bad2", Gender.FEMALE, e_locus=("E", "E")))

        state.breeding_program = BreedingProgram(
            enabled=True,
            stock_limit=4,
            target_colors={BaseColor.GOLDEN},
        )

        cull_surplus_breeders(state)
        marked = [p for p in state.get_pigs_list() if p.marked_for_sale]
        assert len(marked) == 1
        assert "Bad" in marked[0].name

    def test_all_matching_no_replacement(self):
        """No replacement when all adults match the target."""
        state = GameState()
        state.add_guinea_pig(_make_pig("G1", Gender.MALE, e_locus=("e", "e")))
        state.add_guinea_pig(_make_pig("G2", Gender.FEMALE, e_locus=("e", "e")))
        state.add_guinea_pig(_make_pig("G3", Gender.FEMALE, e_locus=("e", "e")))

        state.breeding_program = BreedingProgram(
            enabled=True,
            stock_limit=4,
            target_colors={BaseColor.GOLDEN},
        )

        cull_surplus_breeders(state)
        assert all(not p.marked_for_sale for p in state.get_pigs_list())

    def test_gender_balance_respected(self):
        """Never sells the last male or last female."""
        state = GameState()
        # 1 male (non-matching) + 3 females (non-matching)
        state.add_guinea_pig(_make_pig("OnlyMale", Gender.MALE, e_locus=("E", "E")))
        state.add_guinea_pig(_make_pig("F1", Gender.FEMALE, e_locus=("E", "E")))
        state.add_guinea_pig(_make_pig("F2", Gender.FEMALE, e_locus=("E", "E")))
        state.add_guinea_pig(_make_pig("F3", Gender.FEMALE, e_locus=("E", "E")))

        state.breeding_program = BreedingProgram(
            enabled=True,
            stock_limit=4,
            target_colors={BaseColor.GOLDEN},
        )

        cull_surplus_breeders(state)
        marked = [p for p in state.get_pigs_list() if p.marked_for_sale]
        # Should mark a female, not the only male
        assert len(marked) == 1
        assert marked[0].gender == Gender.FEMALE

    def test_pregnant_pigs_skipped(self):
        """Pregnant pigs are never marked by active replacement."""
        state = GameState()
        state.add_guinea_pig(_make_pig("M1", Gender.MALE, e_locus=("e", "e")))
        pregnant = _make_pig("PregnantBad", Gender.FEMALE, e_locus=("E", "E"))
        pregnant.is_pregnant = True
        state.add_guinea_pig(pregnant)
        # Another non-matching female (not pregnant)
        state.add_guinea_pig(_make_pig("Bad", Gender.FEMALE, e_locus=("E", "E")))
        # Pad to stock_limit so active replacement fires (len == limit)
        state.add_guinea_pig(_make_pig("M2", Gender.MALE, e_locus=("e", "e")))

        state.breeding_program = BreedingProgram(
            enabled=True,
            stock_limit=4,
            target_colors={BaseColor.GOLDEN},
        )

        cull_surplus_breeders(state)
        assert not pregnant.marked_for_sale
        # The non-pregnant non-matching female should be marked instead
        bad = next(p for p in state.get_pigs_list() if p.name == "Bad")
        assert bad.marked_for_sale

    def test_disabled_program_no_replacement(self):
        """Disabled program never triggers active replacement."""
        state = GameState()
        state.add_guinea_pig(_make_pig("M1", Gender.MALE, e_locus=("E", "E")))
        state.add_guinea_pig(_make_pig("F1", Gender.FEMALE, e_locus=("E", "E")))

        state.breeding_program = BreedingProgram(
            enabled=False,
            stock_limit=4,
            target_colors={BaseColor.GOLDEN},
        )

        cull_surplus_breeders(state)
        assert all(not p.marked_for_sale for p in state.get_pigs_list())

    def test_no_targets_no_replacement(self):
        """No replacement when no target traits are set."""
        state = GameState()
        state.add_guinea_pig(_make_pig("M1", Gender.MALE))
        state.add_guinea_pig(_make_pig("F1", Gender.FEMALE))

        state.breeding_program = BreedingProgram(enabled=True, stock_limit=4)

        cull_surplus_breeders(state)
        assert all(not p.marked_for_sale for p in state.get_pigs_list())

    def test_carrier_kept_with_genetics_lab(self):
        """Carrier pigs are not replaced when genetics lab is present and keep_carriers is on."""
        state = GameState()
        from big_pig_farm.entities.facilities import Facility, FacilityType
        lab = Facility.create(FacilityType.GENETICS_LAB, 1, 1)
        state.add_facility(lab)

        # Carrier: Bb (carries chocolate allele but shows black)
        state.add_guinea_pig(_make_pig("Carrier", Gender.MALE, b_locus=("B", "b")))
        state.add_guinea_pig(_make_pig("Match", Gender.FEMALE, b_locus=("b", "b")))

        state.breeding_program = BreedingProgram(
            enabled=True,
            stock_limit=4,
            target_colors={BaseColor.CHOCOLATE},
            keep_carriers=True,
        )

        cull_surplus_breeders(state)
        carrier = next(p for p in state.get_pigs_list() if p.name == "Carrier")
        assert not carrier.marked_for_sale

    def test_below_limit_no_replacement(self):
        """No replacement when below stock limit — need more pigs, not fewer."""
        state = GameState()
        # Only 3 pigs, stock_limit=4 → below limit
        state.add_guinea_pig(_make_pig("M1", Gender.MALE, e_locus=("e", "e")))
        state.add_guinea_pig(_make_pig("F1", Gender.FEMALE, e_locus=("e", "e")))
        state.add_guinea_pig(_make_pig("BadF", Gender.FEMALE, e_locus=("E", "E")))

        state.breeding_program = BreedingProgram(
            enabled=True,
            stock_limit=4,
            target_colors={BaseColor.GOLDEN},
        )

        cull_surplus_breeders(state)
        assert all(not p.marked_for_sale for p in state.get_pigs_list())

    def test_worst_scoring_chosen_first(self):
        """The non-matching pig with the lowest breeding value is sold first."""
        state = GameState()
        state.add_guinea_pig(_make_pig("Good", Gender.MALE, e_locus=("e", "e")))
        state.add_guinea_pig(_make_pig("GoodF", Gender.FEMALE, e_locus=("e", "e")))
        # Bad1: has one 'e' allele (carrier) — slightly better
        state.add_guinea_pig(_make_pig("Bad1", Gender.MALE, e_locus=("E", "e")))
        # Bad2: no 'e' alleles at all — worst
        state.add_guinea_pig(_make_pig("Bad2", Gender.FEMALE, e_locus=("E", "E")))

        state.breeding_program = BreedingProgram(
            enabled=True,
            stock_limit=4,
            target_colors={BaseColor.GOLDEN},
        )

        cull_surplus_breeders(state)
        marked = [p for p in state.get_pigs_list() if p.marked_for_sale]
        assert len(marked) == 1
        assert marked[0].name == "Bad2"

    def test_only_one_marked_per_pass(self):
        """Active replacement marks at most 1 pig per call."""
        state = GameState()
        state.add_guinea_pig(_make_pig("M1", Gender.MALE, e_locus=("e", "e")))
        state.add_guinea_pig(_make_pig("F1", Gender.FEMALE, e_locus=("e", "e")))
        # 3 non-matching pigs
        state.add_guinea_pig(_make_pig("Bad1", Gender.MALE, e_locus=("E", "E")))
        state.add_guinea_pig(_make_pig("Bad2", Gender.FEMALE, e_locus=("E", "E")))
        state.add_guinea_pig(_make_pig("Bad3", Gender.FEMALE, e_locus=("E", "E")))

        state.breeding_program = BreedingProgram(
            enabled=True,
            stock_limit=5,  # Exactly at limit so active replacement fires
            target_colors={BaseColor.GOLDEN},
        )

        cull_surplus_breeders(state)
        marked = [p for p in state.get_pigs_list() if p.marked_for_sale]
        assert len(marked) == 1

    def test_diversity_only_no_targets(self):
        """With maximize_diversity and no targets, lowest-diversity pig is replaced."""
        state = GameState()
        # 3 black pigs (duplicates) + 1 golden pig (unique phenotype)
        state.add_guinea_pig(_make_pig("B1", Gender.MALE, age_days=5.0))
        state.add_guinea_pig(_make_pig("B2", Gender.FEMALE, age_days=5.0))
        state.add_guinea_pig(_make_pig("B3", Gender.FEMALE, age_days=5.0))
        state.add_guinea_pig(_make_pig("Gold", Gender.MALE, age_days=5.0, e_locus=("e", "e")))

        state.breeding_program = BreedingProgram(
            enabled=True,
            maximize_diversity=True,
            stock_limit=4,
            # No target_colors — diversity-only mode
        )

        cull_surplus_breeders(state)
        marked = [p for p in state.get_pigs_list() if p.marked_for_sale]
        assert len(marked) == 1
        # One of the duplicate blacks should be marked, not the unique golden
        assert "B" in marked[0].name

    def test_diversity_only_skips_when_not_enabled(self):
        """Without maximize_diversity and no targets, no replacement happens."""
        state = GameState()
        state.add_guinea_pig(_make_pig("M1", Gender.MALE))
        state.add_guinea_pig(_make_pig("F1", Gender.FEMALE))

        state.breeding_program = BreedingProgram(
            enabled=True,
            maximize_diversity=False,
            stock_limit=4,
        )

        cull_surplus_breeders(state)
        assert all(not p.marked_for_sale for p in state.get_pigs_list())


class TestGenderBalanceHelper:
    """Tests for the _would_break_gender_balance helper."""

    def test_last_male_protected(self):
        """Selling the only male would break balance."""
        male = _make_pig("M1", Gender.MALE)
        f1 = _make_pig("F1", Gender.FEMALE)
        f2 = _make_pig("F2", Gender.FEMALE)
        assert _would_break_gender_balance(male, [male, f1, f2])

    def test_last_female_protected(self):
        """Selling the only female would break balance."""
        m1 = _make_pig("M1", Gender.MALE)
        m2 = _make_pig("M2", Gender.MALE)
        female = _make_pig("F1", Gender.FEMALE)
        assert _would_break_gender_balance(female, [m1, m2, female])

    def test_surplus_gender_ok(self):
        """Selling one of multiple males is fine."""
        m1 = _make_pig("M1", Gender.MALE)
        m2 = _make_pig("M2", Gender.MALE)
        f1 = _make_pig("F1", Gender.FEMALE)
        assert not _would_break_gender_balance(m1, [m1, m2, f1])
