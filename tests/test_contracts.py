"""Tests for the breeding contracts system."""

import pytest

from big_pig_farm.economy.contracts import (
    BreedingContract,
    ContractBoard,
    ContractDifficulty,
    generate_contracts,
)
from big_pig_farm.entities.genetics import (
    BaseColor,
    Pattern,
    ColorIntensity,
    RoanType,
    Rarity,
    Genotype,
    Phenotype,
    calculate_phenotype,
)
from big_pig_farm.entities.guinea_pig import GuineaPig, Gender, Position


def _make_pig(
    base_color: BaseColor = BaseColor.BLACK,
    pattern: Pattern = Pattern.SOLID,
    intensity: ColorIntensity = ColorIntensity.FULL,
    roan: RoanType = RoanType.NONE,
) -> GuineaPig:
    """Create a pig with a specific phenotype for testing."""
    # Build a genotype that produces the desired phenotype
    e_locus = ("E", "E") if base_color in (BaseColor.BLACK, BaseColor.CHOCOLATE) else ("e", "e")
    b_locus = ("B", "B") if base_color in (BaseColor.BLACK, BaseColor.GOLDEN) else ("b", "b")

    if pattern == Pattern.SOLID:
        s_locus = ("S", "S")
    elif pattern == Pattern.DUTCH:
        s_locus = ("S", "s")
    else:
        s_locus = ("s", "s")

    if intensity == ColorIntensity.HIMALAYAN:
        c_locus = ("ch", "ch")
    else:
        # FULL and CHINCHILLA both map to C/C since C is dominant.
        # Note: CHINCHILLA can't currently be produced by the genotype system
        # (C/ch has dominant C -> FULL, ch/ch -> HIMALAYAN).
        c_locus = ("C", "C")

    r_locus = ("R", "r") if roan == RoanType.ROAN else ("r", "r")

    genotype = Genotype(
        e_locus=e_locus, b_locus=b_locus, s_locus=s_locus,
        c_locus=c_locus, r_locus=r_locus,
    )
    phenotype = calculate_phenotype(genotype)
    return GuineaPig(
        name="TestPig", genotype=genotype, phenotype=phenotype,
        gender=Gender.MALE, position=Position(x=5.0, y=5.0),
    )


class TestContractMatching:
    """Tests for contract-pig matching."""

    def test_easy_contract_matches_color(self):
        """Easy contract (color only) should match any pig of that color."""
        contract = BreedingContract(
            required_color=BaseColor.BLACK,
            difficulty=ContractDifficulty.EASY,
            reward=50,
            deadline_day=100,
        )
        black_pig = _make_pig(base_color=BaseColor.BLACK)
        golden_pig = _make_pig(base_color=BaseColor.GOLDEN)

        assert contract.matches_pig(black_pig) is True
        assert contract.matches_pig(golden_pig) is False

    def test_medium_contract_requires_pattern(self):
        """Medium contract should check both color and pattern."""
        contract = BreedingContract(
            required_color=BaseColor.BLACK,
            required_pattern=Pattern.DUTCH,
            difficulty=ContractDifficulty.MEDIUM,
            reward=150,
            deadline_day=100,
        )
        dutch_black = _make_pig(base_color=BaseColor.BLACK, pattern=Pattern.DUTCH)
        solid_black = _make_pig(base_color=BaseColor.BLACK, pattern=Pattern.SOLID)

        assert contract.matches_pig(dutch_black) is True
        assert contract.matches_pig(solid_black) is False

    def test_expert_contract_requires_all(self):
        """Expert contract should check all 4 traits."""
        contract = BreedingContract(
            required_color=BaseColor.CHOCOLATE,
            required_pattern=Pattern.DALMATIAN,
            required_intensity=ColorIntensity.HIMALAYAN,
            required_roan=RoanType.ROAN,
            difficulty=ContractDifficulty.EXPERT,
            reward=800,
            deadline_day=100,
        )
        exact_match = _make_pig(
            base_color=BaseColor.CHOCOLATE,
            pattern=Pattern.DALMATIAN,
            intensity=ColorIntensity.HIMALAYAN,
            roan=RoanType.ROAN,
        )
        partial_match = _make_pig(
            base_color=BaseColor.CHOCOLATE,
            pattern=Pattern.DALMATIAN,
            intensity=ColorIntensity.HIMALAYAN,
            roan=RoanType.NONE,  # Wrong roan
        )

        assert contract.matches_pig(exact_match) is True
        assert contract.matches_pig(partial_match) is False

    def test_fulfilled_contract_doesnt_match(self):
        """Fulfilled contracts should not match any pig."""
        contract = BreedingContract(
            required_color=BaseColor.BLACK,
            difficulty=ContractDifficulty.EASY,
            reward=50,
            deadline_day=100,
            fulfilled=True,
        )
        pig = _make_pig(base_color=BaseColor.BLACK)
        assert contract.matches_pig(pig) is False


class TestContractBoard:
    """Tests for ContractBoard management."""

    def test_fulfill_contract(self):
        """Fulfilling a contract should return it and increment counter."""
        board = ContractBoard()
        contract = BreedingContract(
            required_color=BaseColor.BLACK,
            difficulty=ContractDifficulty.EASY,
            reward=75,
            deadline_day=100,
        )
        board.active_contracts = [contract]

        pig = _make_pig(base_color=BaseColor.BLACK)
        matched = board.check_and_fulfill(pig)

        assert matched is not None
        assert matched.reward == 75
        assert board.completed_contracts == 1
        assert board.total_contract_earnings == 75

    def test_no_match_returns_none(self):
        """No matching contract should return None."""
        board = ContractBoard()
        contract = BreedingContract(
            required_color=BaseColor.GOLDEN,
            difficulty=ContractDifficulty.EASY,
            reward=50,
            deadline_day=100,
        )
        board.active_contracts = [contract]

        pig = _make_pig(base_color=BaseColor.BLACK)
        assert board.check_and_fulfill(pig) is None

    def test_remove_fulfilled(self):
        """remove_fulfilled should clear fulfilled contracts."""
        board = ContractBoard()
        c1 = BreedingContract(required_color=BaseColor.BLACK, reward=50, deadline_day=100)
        c2 = BreedingContract(required_color=BaseColor.GOLDEN, reward=75, deadline_day=100)
        c1.fulfilled = True
        board.active_contracts = [c1, c2]

        board.remove_fulfilled()
        assert len(board.active_contracts) == 1
        assert board.active_contracts[0].required_color == BaseColor.GOLDEN

    def test_check_expiry(self):
        """Expired contracts should be removed."""
        board = ContractBoard()
        expired = BreedingContract(
            required_color=BaseColor.BLACK, reward=50, deadline_day=5,
        )
        active = BreedingContract(
            required_color=BaseColor.GOLDEN, reward=75, deadline_day=100,
        )
        board.active_contracts = [expired, active]

        removed = board.check_expiry(game_day=10)
        assert len(removed) == 1
        assert len(board.active_contracts) == 1

    def test_needs_refresh(self):
        """Refresh should trigger after configured interval."""
        board = ContractBoard(last_refresh_day=1)
        assert board.needs_refresh(game_day=5) is False
        assert board.needs_refresh(game_day=11) is True


class TestContractGeneration:
    """Tests for contract generation."""

    def test_generates_correct_count(self):
        """Should generate appropriate number of contracts."""
        contracts = generate_contracts(farm_tier=1, game_day=1)
        assert 1 <= len(contracts) <= 4

    def test_tier1_only_easy(self):
        """Tier 1 should only generate EASY contracts."""
        for _ in range(20):
            contracts = generate_contracts(farm_tier=1, game_day=1)
            for c in contracts:
                assert c.difficulty == ContractDifficulty.EASY

    def test_higher_tiers_have_harder_contracts(self):
        """Tier 4 should be able to generate EXPERT contracts."""
        found_expert = False
        for _ in range(50):
            contracts = generate_contracts(farm_tier=4, game_day=1)
            for c in contracts:
                if c.difficulty == ContractDifficulty.EXPERT:
                    found_expert = True
                    break
            if found_expert:
                break
        assert found_expert, "Expected at least one EXPERT contract from tier 4 in 50 attempts"

    def test_contracts_have_valid_deadlines(self):
        """All contracts should have a deadline after creation day."""
        contracts = generate_contracts(farm_tier=3, game_day=10)
        for c in contracts:
            assert c.deadline_day > c.created_day

    def test_requirements_text(self):
        """Requirements text should be readable."""
        contract = BreedingContract(
            required_color=BaseColor.CHOCOLATE,
            required_pattern=Pattern.DUTCH,
            difficulty=ContractDifficulty.MEDIUM,
        )
        text = contract.requirements_text
        assert "Dutch" in text
        assert "Chocolate" in text
