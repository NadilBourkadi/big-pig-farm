"""Breeding contracts - NPC orders requesting specific phenotypes."""

import random
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from big_pig_farm.entities.genetics import BaseColor, Pattern, ColorIntensity, RoanType
from big_pig_farm.entities.guinea_pig import GuineaPig


class ContractDifficulty(str, Enum):
    """Contract difficulty tier."""
    EASY = "easy"        # Color only
    MEDIUM = "medium"    # Color + pattern
    HARD = "hard"        # Color + pattern + intensity
    EXPERT = "expert"    # All 4 traits


class BreedingContract(BaseModel):
    """A breeding contract requesting a specific phenotype."""
    id: UUID = Field(default_factory=uuid4)
    description: str = ""
    required_color: Optional[BaseColor] = None
    required_pattern: Optional[Pattern] = None
    required_intensity: Optional[ColorIntensity] = None
    required_roan: Optional[RoanType] = None
    difficulty: ContractDifficulty = ContractDifficulty.EASY
    reward: int = 50
    deadline_day: int = 0
    created_day: int = 0
    fulfilled: bool = False

    def matches_pig(self, pig: GuineaPig) -> bool:
        """Check if a pig matches all requirements of this contract."""
        if self.fulfilled:
            return False
        phenotype = pig.phenotype
        if self.required_color and phenotype.base_color != self.required_color:
            return False
        if self.required_pattern and phenotype.pattern != self.required_pattern:
            return False
        if self.required_intensity and phenotype.intensity != self.required_intensity:
            return False
        if self.required_roan and phenotype.roan != self.required_roan:
            return False
        return True

    @property
    def requirements_text(self) -> str:
        """Human-readable description of requirements."""
        parts = []
        if self.required_roan and self.required_roan == RoanType.ROAN:
            parts.append("Roan")
        if self.required_intensity and self.required_intensity != ColorIntensity.FULL:
            parts.append(self.required_intensity.value.title())
        if self.required_pattern and self.required_pattern != Pattern.SOLID:
            parts.append(self.required_pattern.value.title())
        if self.required_color:
            color_names = {
                BaseColor.BLACK: "Black",
                BaseColor.CHOCOLATE: "Chocolate",
                BaseColor.GOLDEN: "Golden",
                BaseColor.LIGHT_GOLDEN: "Cream",
            }
            parts.append(color_names.get(self.required_color, self.required_color.value))
        if not parts:
            return "Any pig"
        return " ".join(parts)


class ContractBoard(BaseModel):
    """Manages active breeding contracts."""
    active_contracts: list[BreedingContract] = Field(default_factory=list)
    completed_contracts: int = 0
    total_contract_earnings: int = 0
    last_refresh_day: int = 0

    def check_and_fulfill(self, pig: GuineaPig) -> Optional[BreedingContract]:
        """Check if a pig matches any active contract. Returns matched contract or None."""
        for contract in self.active_contracts:
            if contract.matches_pig(pig):
                contract.fulfilled = True
                self.completed_contracts += 1
                self.total_contract_earnings += contract.reward
                return contract
        return None

    def remove_fulfilled(self) -> None:
        """Remove fulfilled contracts from active list."""
        self.active_contracts = [c for c in self.active_contracts if not c.fulfilled]

    def check_expiry(self, game_day: int) -> list[BreedingContract]:
        """Remove and return expired contracts."""
        expired = [c for c in self.active_contracts if game_day > c.deadline_day and not c.fulfilled]
        self.active_contracts = [c for c in self.active_contracts if c not in expired]
        return expired

    def needs_refresh(self, game_day: int) -> bool:
        """Check if contracts should be refreshed."""
        from big_pig_farm.data.config import CONTRACTS
        return game_day - self.last_refresh_day >= CONTRACTS.REFRESH_INTERVAL_DAYS


def generate_contracts(farm_tier: int, game_day: int) -> list[BreedingContract]:
    """Generate a set of contracts appropriate for the farm tier."""
    from big_pig_farm.data.config import CONTRACTS

    contracts = []
    num_contracts = min(CONTRACTS.MAX_ACTIVE_CONTRACTS, max(2, farm_tier))

    # Determine available difficulties by tier
    available_difficulties = []
    if farm_tier >= 1:
        available_difficulties.append(ContractDifficulty.EASY)
    if farm_tier >= 2:
        available_difficulties.append(ContractDifficulty.MEDIUM)
    if farm_tier >= 3:
        available_difficulties.append(ContractDifficulty.HARD)
    if farm_tier >= 4:
        available_difficulties.append(ContractDifficulty.EXPERT)

    for _ in range(num_contracts):
        difficulty = random.choice(available_difficulties)
        contract = _generate_single_contract(difficulty, game_day)
        contracts.append(contract)

    return contracts


def _generate_single_contract(difficulty: ContractDifficulty, game_day: int) -> BreedingContract:
    """Generate a single contract of the given difficulty."""
    from big_pig_farm.data.config import CONTRACTS

    required_color = random.choice(list(BaseColor))
    required_pattern = None
    required_intensity = None
    required_roan = None

    if difficulty in (ContractDifficulty.MEDIUM, ContractDifficulty.HARD, ContractDifficulty.EXPERT):
        required_pattern = random.choice(list(Pattern))

    if difficulty in (ContractDifficulty.HARD, ContractDifficulty.EXPERT):
        required_intensity = random.choice(list(ColorIntensity))

    if difficulty == ContractDifficulty.EXPERT:
        required_roan = random.choice(list(RoanType))

    # Calculate reward based on difficulty
    reward_ranges = {
        ContractDifficulty.EASY: (CONTRACTS.EASY_REWARD_MIN, CONTRACTS.EASY_REWARD_MAX),
        ContractDifficulty.MEDIUM: (CONTRACTS.MEDIUM_REWARD_MIN, CONTRACTS.MEDIUM_REWARD_MAX),
        ContractDifficulty.HARD: (CONTRACTS.HARD_REWARD_MIN, CONTRACTS.HARD_REWARD_MAX),
        ContractDifficulty.EXPERT: (CONTRACTS.EXPERT_REWARD_MIN, CONTRACTS.EXPERT_REWARD_MAX),
    }
    min_reward, max_reward = reward_ranges[difficulty]
    reward = random.randint(min_reward, max_reward)

    deadline_day = game_day + CONTRACTS.EXPIRY_DAYS

    contract = BreedingContract(
        required_color=required_color,
        required_pattern=required_pattern,
        required_intensity=required_intensity,
        required_roan=required_roan,
        difficulty=difficulty,
        reward=reward,
        deadline_day=deadline_day,
        created_day=game_day,
    )
    contract.description = f"Deliver a {contract.requirements_text} pig"

    return contract
