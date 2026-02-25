"""Breeding contracts - NPC orders requesting specific phenotypes."""

import random
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from big_pig_farm.data.config import BIOME, CONTRACTS
from big_pig_farm.entities.biomes import BiomeType
from big_pig_farm.entities.genetics import BaseColor, ColorIntensity, Pattern, RoanType
from big_pig_farm.entities.guinea_pig import GuineaPig

if TYPE_CHECKING:
    from big_pig_farm.game.state import GameState


class ContractDifficulty(str, Enum):
    """Contract difficulty tier."""
    EASY = "easy"        # Color only
    MEDIUM = "medium"    # Color + pattern
    HARD = "hard"        # Color + pattern + intensity
    EXPERT = "expert"    # All 4 traits
    LEGENDARY = "legendary"  # All 4 traits + roan (requires VIP perk)


class BreedingContract(BaseModel):
    """A breeding contract requesting a specific phenotype."""
    id: UUID = Field(default_factory=uuid4)
    description: str = ""
    required_color: BaseColor | None = None
    required_pattern: Pattern | None = None
    required_intensity: ColorIntensity | None = None
    required_roan: RoanType | None = None
    required_biome: BiomeType | None = None
    difficulty: ContractDifficulty = ContractDifficulty.EASY
    reward: int = 50
    deadline_day: int = 0
    created_day: int = 0
    fulfilled: bool = False

    def matches_pig(self, pig: GuineaPig, farm=None) -> bool:
        """Check if a pig matches all requirements of this contract.

        Args:
            pig: The pig to check
            farm: FarmGrid for biome lookups (needed if required_biome is set)
        """
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
        if self.required_biome:
            # Check pig's birth area biome
            if not pig.birth_area_id or not farm:
                return False
            birth_area = farm.get_area_by_id(pig.birth_area_id)
            if not birth_area or birth_area.biome != self.required_biome:
                return False
        return True

    @property
    def breeding_hint(self) -> str:
        """Hint about which bloodlines help produce the required traits."""
        hints = []
        if self.required_color == BaseColor.CREAM:
            hints.append("Golden + Chocolate bloodlines")
        elif self.required_color == BaseColor.GOLDEN:
            hints.append("Golden bloodline (Tier 2)")
        elif self.required_color == BaseColor.CHOCOLATE:
            hints.append("Chocolate bloodline")
        elif self.required_color == BaseColor.BLUE:
            hints.append("Breed in Alpine biome (Dilution)")
        elif self.required_color == BaseColor.LILAC:
            hints.append("Chocolate bloodline + Alpine biome")
        elif self.required_color == BaseColor.SAFFRON:
            hints.append("Golden bloodline + Alpine biome")
        elif self.required_color == BaseColor.SMOKE:
            hints.append("Golden + Chocolate + Alpine biome")

        if self.required_pattern in (Pattern.DUTCH, Pattern.DALMATIAN):
            hints.append("Spotted bloodline")

        if self.required_intensity in (ColorIntensity.CHINCHILLA, ColorIntensity.HIMALAYAN):
            hints.append("Silver bloodline (Tier 2)")

        if self.required_roan == RoanType.ROAN:
            hints.append("Roan bloodline (Tier 3)")

        return " + ".join(hints) if hints else ""

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
                BaseColor.CREAM: "Cream",
                BaseColor.BLUE: "Blue",
                BaseColor.LILAC: "Lilac",
                BaseColor.SAFFRON: "Saffron",
                BaseColor.SMOKE: "Smoke",
            }
            parts.append(color_names.get(self.required_color, self.required_color.value))
        if self.required_biome:
            from big_pig_farm.entities.biomes import BIOMES
            biome_name = BIOMES[self.required_biome].display_name
            parts.append(f"(born in {biome_name})")
        if not parts:
            return "Any pig"
        return " ".join(parts)


class ContractBoard(BaseModel):
    """Manages active breeding contracts."""
    active_contracts: list[BreedingContract] = Field(default_factory=list)
    completed_contracts: int = 0
    total_contract_earnings: int = 0
    last_refresh_day: int = 0

    def check_and_fulfill(self, pig: GuineaPig, farm=None) -> BreedingContract | None:
        """Check if a pig matches any active contract. Returns matched contract or None."""
        for contract in self.active_contracts:
            if contract.matches_pig(pig, farm=farm):
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
        return game_day - self.last_refresh_day >= CONTRACTS.REFRESH_INTERVAL_DAYS


def generate_contracts(
    farm_tier: int,
    game_day: int,
    available_biomes: list[BiomeType] | None = None,
    game_state: "GameState | None" = None,
) -> list[BreedingContract]:
    """Generate a set of contracts appropriate for the farm tier."""
    contracts = []
    max_contracts = CONTRACTS.MAX_ACTIVE_CONTRACTS
    # Contract Negotiator perk: +1 max active contract slot
    if game_state and game_state.has_upgrade("contract_negotiator"):
        max_contracts += 1
    num_contracts = min(max_contracts, max(2, farm_tier))

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
    # VIP Contracts perk: unlock LEGENDARY difficulty at tier 5
    if farm_tier >= 5 and game_state and game_state.has_upgrade("vip_contracts"):
        available_difficulties.append(ContractDifficulty.LEGENDARY)

    for _ in range(num_contracts):
        difficulty = random.choice(available_difficulties)
        contract = _generate_single_contract(difficulty, game_day, farm_tier, available_biomes)
        contracts.append(contract)

    return contracts


def _filter_by_tier(values: list, tier_map: dict[object, int], farm_tier: int) -> list:
    """Filter enum values to those available at the given farm tier."""
    return [v for v in values if tier_map.get(v, 1) <= farm_tier]


# Minimum farm tier required for each trait to appear in contracts
COLOR_TIER_REQUIREMENTS: dict[BaseColor, int] = {
    BaseColor.BLACK: 1,
    BaseColor.CHOCOLATE: 1,
    BaseColor.GOLDEN: 1,
    BaseColor.CREAM: 2,
    BaseColor.BLUE: 3,
    BaseColor.LILAC: 3,
    BaseColor.SAFFRON: 3,
    BaseColor.SMOKE: 4,
}

PATTERN_TIER_REQUIREMENTS: dict[Pattern, int] = {
    Pattern.SOLID: 1,
    Pattern.DUTCH: 1,
    Pattern.DALMATIAN: 1,
}

INTENSITY_TIER_REQUIREMENTS: dict[ColorIntensity, int] = {
    ColorIntensity.FULL: 1,
    ColorIntensity.CHINCHILLA: 2,
    ColorIntensity.HIMALAYAN: 2,
}

ROAN_TIER_REQUIREMENTS: dict[RoanType, int] = {
    RoanType.NONE: 1,
    RoanType.ROAN: 3,
}


def _generate_single_contract(
    difficulty: ContractDifficulty,
    game_day: int,
    farm_tier: int,
    available_biomes: list[BiomeType] | None = None,
) -> BreedingContract:
    """Generate a single contract of the given difficulty."""
    available_colors = _filter_by_tier(list(BaseColor), COLOR_TIER_REQUIREMENTS, farm_tier)
    required_color = random.choice(available_colors)
    required_pattern = None
    required_intensity = None
    required_roan = None
    required_biome = None

    if difficulty in (ContractDifficulty.MEDIUM, ContractDifficulty.HARD,
                      ContractDifficulty.EXPERT, ContractDifficulty.LEGENDARY):
        available_patterns = _filter_by_tier(list(Pattern), PATTERN_TIER_REQUIREMENTS, farm_tier)
        required_pattern = random.choice(available_patterns)

    if difficulty in (ContractDifficulty.HARD, ContractDifficulty.EXPERT,
                      ContractDifficulty.LEGENDARY):
        available_intensities = _filter_by_tier(
            list(ColorIntensity), INTENSITY_TIER_REQUIREMENTS, farm_tier
        )
        required_intensity = random.choice(available_intensities)

    if difficulty in (ContractDifficulty.EXPERT, ContractDifficulty.LEGENDARY):
        available_roans = _filter_by_tier(list(RoanType), ROAN_TIER_REQUIREMENTS, farm_tier)
        required_roan = random.choice(available_roans)

    # LEGENDARY forces roan requirement
    if difficulty == ContractDifficulty.LEGENDARY:
        required_roan = RoanType.ROAN

    # Biome requirement: tier 3+, HARD/EXPERT/LEGENDARY, 30% chance
    if (farm_tier >= 3
            and available_biomes
            and len(available_biomes) > 1
            and difficulty in (ContractDifficulty.HARD, ContractDifficulty.EXPERT,
                              ContractDifficulty.LEGENDARY)
            and random.random() < BIOME.BIOME_CONTRACT_CHANCE):
        required_biome = random.choice(available_biomes)

    # Calculate reward based on difficulty
    reward_ranges = {
        ContractDifficulty.EASY: (CONTRACTS.EASY_REWARD_MIN, CONTRACTS.EASY_REWARD_MAX),
        ContractDifficulty.MEDIUM: (CONTRACTS.MEDIUM_REWARD_MIN, CONTRACTS.MEDIUM_REWARD_MAX),
        ContractDifficulty.HARD: (CONTRACTS.HARD_REWARD_MIN, CONTRACTS.HARD_REWARD_MAX),
        ContractDifficulty.EXPERT: (CONTRACTS.EXPERT_REWARD_MIN, CONTRACTS.EXPERT_REWARD_MAX),
        ContractDifficulty.LEGENDARY: (CONTRACTS.LEGENDARY_REWARD_MIN, CONTRACTS.LEGENDARY_REWARD_MAX),
    }
    min_reward, max_reward = reward_ranges[difficulty]
    reward = random.randint(min_reward, max_reward)

    # Biome contracts get a reward bonus
    if required_biome:
        reward = int(reward * (1 + BIOME.BIOME_CONTRACT_REWARD_BONUS))

    deadline_day = game_day + CONTRACTS.EXPIRY_DAYS

    contract = BreedingContract(
        required_color=required_color,
        required_pattern=required_pattern,
        required_intensity=required_intensity,
        required_roan=required_roan,
        required_biome=required_biome,
        difficulty=difficulty,
        reward=reward,
        deadline_day=deadline_day,
        created_day=game_day,
    )
    contract.description = f"Deliver a {contract.requirements_text} pig"

    return contract
