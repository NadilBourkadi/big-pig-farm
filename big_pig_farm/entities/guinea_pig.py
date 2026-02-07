"""Guinea pig entity - the core creature of the game."""

from __future__ import annotations

import random
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from big_pig_farm.entities.genetics import (
    Genotype,
    Phenotype,
    Rarity,
    calculate_phenotype,
)

if TYPE_CHECKING:
    pass

from big_pig_farm.data.config import BREEDING, ECONOMY, NEEDS, SIMULATION


class Gender(str, Enum):
    """Guinea pig gender."""
    MALE = "male"
    FEMALE = "female"


class AgeGroup(str, Enum):
    """Life stage of a guinea pig."""
    BABY = "baby"
    ADULT = "adult"
    SENIOR = "senior"


class BehaviorState(str, Enum):
    """Current behavior/activity state."""
    IDLE = "idle"
    WANDERING = "wandering"
    EATING = "eating"
    DRINKING = "drinking"
    PLAYING = "playing"
    SLEEPING = "sleeping"
    SOCIALIZING = "socializing"
    COURTING = "courting"


class Personality(str, Enum):
    """Personality traits that modify behavior."""
    GREEDY = "greedy"      # +50% hunger decay, eats more
    LAZY = "lazy"          # -30% energy decay, sleeps more
    PLAYFUL = "playful"    # +50% boredom decay, uses toys more
    SHY = "shy"            # Avoids other pigs, prefers hideouts
    SOCIAL = "social"      # Seeks other pigs, happiness from groups
    BRAVE = "brave"        # Explores more, less hideout time
    PICKY = "picky"        # Prefers high-quality facilities


class Needs(BaseModel):
    """Guinea pig needs that must be maintained."""
    hunger: float = Field(default=100.0, ge=0.0, le=100.0)
    thirst: float = Field(default=100.0, ge=0.0, le=100.0)
    energy: float = Field(default=100.0, ge=0.0, le=100.0)
    happiness: float = Field(default=75.0, ge=0.0, le=100.0)
    health: float = Field(default=100.0, ge=0.0, le=100.0)

    # Secondary needs
    social: float = Field(default=50.0, ge=0.0, le=100.0)
    boredom: float = Field(default=0.0, ge=0.0, le=100.0)

    def clamp_all(self) -> None:
        """Ensure all values stay within bounds."""
        self.hunger = max(0.0, min(100.0, self.hunger))
        self.thirst = max(0.0, min(100.0, self.thirst))
        self.energy = max(0.0, min(100.0, self.energy))
        self.happiness = max(0.0, min(100.0, self.happiness))
        self.health = max(0.0, min(100.0, self.health))
        self.social = max(0.0, min(100.0, self.social))
        self.boredom = max(0.0, min(100.0, self.boredom))


class Position(BaseModel):
    """Position on the farm grid."""
    x: float = 0.0
    y: float = 0.0

    def distance_to(self, other: "Position") -> float:
        """Calculate distance to another position."""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def grid_pos(self) -> tuple[int, int]:
        """Get integer grid position."""
        return (int(self.x), int(self.y))


class GuineaPig(BaseModel):
    """A guinea pig entity."""
    id: UUID = Field(default_factory=uuid4)
    name: str

    # Genetics
    genotype: Genotype
    phenotype: Phenotype

    # Demographics
    gender: Gender
    birth_time: datetime = Field(default_factory=datetime.now)
    age_days: float = 0.0

    # Traits
    personality: list[Personality] = Field(default_factory=list)

    # State
    needs: Needs = Field(default_factory=Needs)
    behavior_state: BehaviorState = BehaviorState.IDLE
    position: Position = Field(default_factory=Position)

    # Movement
    target_position: Optional[Position] = None
    target_description: Optional[str] = None  # What the pig is trying to do (e.g., "eating at Food Bowl")
    target_facility_id: Optional[UUID] = None  # ID of facility pig is heading to
    path: list[tuple[int, int]] = Field(default_factory=list)

    # Breeding
    is_pregnant: bool = False
    pregnancy_days: float = 0.0
    partner_id: Optional[UUID] = None
    partner_genotype: Optional[Genotype] = None  # Stored at conception for birth
    partner_name: Optional[str] = None  # Stored at conception in case father is sold
    last_birth_age: Optional[float] = None

    # Family
    mother_id: Optional[UUID] = None
    father_id: Optional[UUID] = None
    mother_name: Optional[str] = None
    father_name: Optional[str] = None

    # Breeding control
    breeding_locked: bool = False  # If True, pig won't auto-breed
    marked_for_sale: bool = False  # If True, pig will be auto-sold when it reaches adulthood

    # Origin info (e.g., "Spotted Bloodline" for bloodline pigs)
    origin_tag: Optional[str] = None

    # Behavior log for debugging (recent decisions/actions)
    behavior_log: list[str] = Field(default_factory=list)

    def log_behavior(self, message: str, max_entries: int = 20) -> None:
        """Add an entry to the behavior log, keeping only recent entries."""
        self.behavior_log.append(message)
        if len(self.behavior_log) > max_entries:
            self.behavior_log = self.behavior_log[-max_entries:]

    @classmethod
    def create(
        cls,
        name: str,
        gender: Gender,
        genotype: Optional[Genotype] = None,
        position: Optional[Position] = None,
        age_days: float = 0.0,
        mother_id: Optional[UUID] = None,
        father_id: Optional[UUID] = None,
        mother_name: Optional[str] = None,
        father_name: Optional[str] = None,
    ) -> GuineaPig:
        """Create a new guinea pig with calculated phenotype."""
        if genotype is None:
            genotype = Genotype.random_common()

        phenotype = calculate_phenotype(genotype)

        # Assign 1-2 random personality traits
        traits = list(Personality)
        num_traits = random.randint(1, 2)
        personality = random.sample(traits, num_traits)

        return cls(
            name=name,
            genotype=genotype,
            phenotype=phenotype,
            gender=gender,
            position=position or Position(),
            age_days=age_days,
            personality=personality,
            mother_id=mother_id,
            father_id=father_id,
            mother_name=mother_name,
            father_name=father_name,
        )

    @property
    def age_group(self) -> AgeGroup:
        """Determine life stage based on age."""
        if self.age_days < SIMULATION.ADULT_AGE_DAYS:
            return AgeGroup.BABY
        elif self.age_days >= SIMULATION.SENIOR_AGE_DAYS:
            return AgeGroup.SENIOR
        return AgeGroup.ADULT

    @property
    def is_baby(self) -> bool:
        """Check if this pig is a baby."""
        return self.age_group == AgeGroup.BABY

    @property
    def is_adult(self) -> bool:
        """Check if this pig is an adult (breeding age)."""
        return self.age_group == AgeGroup.ADULT

    @property
    def is_senior(self) -> bool:
        """Check if this pig is a senior."""
        return self.age_group == AgeGroup.SENIOR

    @property
    def can_breed(self) -> bool:
        """Check if this pig can currently breed."""
        if self.breeding_locked:
            return False
        if not self.is_adult:
            return False
        if self.needs.happiness < NEEDS.HIGH_THRESHOLD:
            return False
        if self.is_pregnant:
            return False
        if self.gender == Gender.FEMALE and self.last_birth_age is not None:
            if self.age_days - self.last_birth_age < BREEDING.RECOVERY_DAYS:
                return False
        return True

    @property
    def display_state(self) -> str:
        """Get display string for current state."""
        state_displays = {
            BehaviorState.IDLE: "idle",
            BehaviorState.WANDERING: "walking",
            BehaviorState.EATING: "eating",
            BehaviorState.DRINKING: "eating",  # Similar animation
            BehaviorState.PLAYING: "happy",
            BehaviorState.SLEEPING: "sleeping",
            BehaviorState.SOCIALIZING: "happy",
            BehaviorState.COURTING: "happy",
        }
        return state_displays.get(self.behavior_state, "idle")

    def has_trait(self, trait: Personality) -> bool:
        """Check if pig has a specific personality trait."""
        return trait in self.personality

    def get_value(self) -> int:
        """Calculate the monetary value of this guinea pig."""
        base_value = ECONOMY.COMMON_PIG_VALUE

        multipliers = {
            Rarity.COMMON: 1.0,
            Rarity.UNCOMMON: ECONOMY.UNCOMMON_MULTIPLIER,
            Rarity.RARE: ECONOMY.RARE_MULTIPLIER,
            Rarity.VERY_RARE: ECONOMY.VERY_RARE_MULTIPLIER,
            Rarity.LEGENDARY: ECONOMY.LEGENDARY_MULTIPLIER,
        }

        multiplier = multipliers.get(self.phenotype.rarity, 1.0)
        return int(base_value * multiplier)
