"""Pigdex - collection tracker for all phenotype combinations."""

from typing import Optional

from pydantic import BaseModel, Field

from big_pig_farm.data.config import PIGDEX
from big_pig_farm.entities.genetics import (
    BaseColor,
    Pattern,
    ColorIntensity,
    RoanType,
    Rarity,
    Phenotype,
    calculate_rarity,
)


# All possible phenotype combinations
ALL_BASE_COLORS = list(BaseColor)
ALL_PATTERNS = list(Pattern)
ALL_INTENSITIES = list(ColorIntensity)
ALL_ROAN_TYPES = [RoanType.NONE, RoanType.ROAN]

TOTAL_PHENOTYPES = len(ALL_BASE_COLORS) * len(ALL_PATTERNS) * len(ALL_INTENSITIES) * len(ALL_ROAN_TYPES)
# 4 colors x 3 patterns x 3 intensities x 2 roan = 72


def phenotype_key(phenotype: Phenotype) -> str:
    """Generate a unique string key for a phenotype."""
    return f"{phenotype.base_color.value}:{phenotype.pattern.value}:{phenotype.intensity.value}:{phenotype.roan.value}"


def phenotype_key_from_parts(
    base_color: BaseColor,
    pattern: Pattern,
    intensity: ColorIntensity,
    roan: RoanType,
) -> str:
    """Generate a unique string key from individual trait parts."""
    return f"{base_color.value}:{pattern.value}:{intensity.value}:{roan.value}"


def key_to_display_name(key: str) -> str:
    """Convert a phenotype key back to a display name."""
    parts = key.split(":")
    if len(parts) != 4:
        return key

    base_color = BaseColor(parts[0])
    pattern = Pattern(parts[1])
    intensity = ColorIntensity(parts[2])
    roan = RoanType(parts[3])

    rarity = calculate_rarity(base_color, pattern, intensity, roan)

    phenotype = Phenotype(
        base_color=base_color,
        pattern=pattern,
        intensity=intensity,
        roan=roan,
        rarity=rarity,
    )
    return phenotype.display_name


def key_to_rarity(key: str) -> Rarity:
    """Get the rarity of a phenotype key."""
    parts = key.split(":")
    if len(parts) != 4:
        return Rarity.COMMON

    return calculate_rarity(
        BaseColor(parts[0]),
        Pattern(parts[1]),
        ColorIntensity(parts[2]),
        RoanType(parts[3]),
    )


# Milestone thresholds (as percentage of total)
MILESTONE_THRESHOLDS = [25, 50, 75, 100]


class Pigdex(BaseModel):
    """Tracks all discovered phenotype combinations."""
    discovered: dict[str, int] = Field(default_factory=dict)  # key -> game day discovered
    milestone_rewards_claimed: list[int] = Field(default_factory=list)

    @property
    def total_possible(self) -> int:
        return TOTAL_PHENOTYPES

    @property
    def discovered_count(self) -> int:
        return len(self.discovered)

    @property
    def completion_percent(self) -> float:
        if self.total_possible == 0:
            return 0.0
        return (self.discovered_count / self.total_possible) * 100

    def register_phenotype(self, key: str, game_day: int) -> bool:
        """Register a new phenotype discovery. Returns True if it was new."""
        if key in self.discovered:
            return False
        self.discovered[key] = game_day
        return True

    def check_milestones(self) -> list[int]:
        """Check for newly reached milestones. Returns list of newly reached percentages."""
        newly_reached = []
        for threshold in MILESTONE_THRESHOLDS:
            if threshold in self.milestone_rewards_claimed:
                continue
            required = int(self.total_possible * threshold / 100)
            if self.discovered_count >= required:
                newly_reached.append(threshold)
        return newly_reached

    def claim_milestone(self, threshold: int) -> None:
        """Mark a milestone as claimed."""
        if threshold not in self.milestone_rewards_claimed:
            self.milestone_rewards_claimed.append(threshold)

    def is_discovered(self, key: str) -> bool:
        """Check if a phenotype has been discovered."""
        return key in self.discovered


def get_all_phenotype_keys() -> list[str]:
    """Get all possible phenotype keys in a consistent order."""
    keys = []
    for roan in ALL_ROAN_TYPES:
        for intensity in ALL_INTENSITIES:
            for pattern in ALL_PATTERNS:
                for color in ALL_BASE_COLORS:
                    keys.append(phenotype_key_from_parts(color, pattern, intensity, roan))
    return keys


def get_discovery_reward(rarity: Rarity) -> int:
    """Get the Squeaks reward for discovering a phenotype of the given rarity."""
    rewards = {
        Rarity.COMMON: PIGDEX.COMMON_REWARD,
        Rarity.UNCOMMON: PIGDEX.UNCOMMON_REWARD,
        Rarity.RARE: PIGDEX.RARE_REWARD,
        Rarity.VERY_RARE: PIGDEX.VERY_RARE_REWARD,
        Rarity.LEGENDARY: PIGDEX.LEGENDARY_REWARD,
    }
    return rewards.get(rarity, PIGDEX.COMMON_REWARD)


def get_milestone_reward(threshold: int) -> int:
    """Get the Squeaks reward for reaching a milestone percentage."""
    rewards = {
        25: PIGDEX.MILESTONE_25_REWARD,
        50: PIGDEX.MILESTONE_50_REWARD,
        75: PIGDEX.MILESTONE_75_REWARD,
        100: PIGDEX.MILESTONE_100_REWARD,
    }
    return rewards.get(threshold, 0)
