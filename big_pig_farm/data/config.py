"""Game balance constants and configuration."""

from dataclasses import dataclass
from enum import Enum


class GameSpeed(Enum):
    """Game speed multipliers."""
    PAUSED = 0
    NORMAL = 1
    FAST = 2
    FASTER = 5
    FASTEST = 20


@dataclass(frozen=True)
class NeedsConfig:
    """Configuration for guinea pig needs decay and thresholds."""
    # Decay rates per game hour
    HUNGER_DECAY: float = 5.0
    THIRST_DECAY: float = 8.0
    ENERGY_DECAY: float = 3.0
    HAPPINESS_BASE_DECAY: float = 2.0

    # Thresholds
    CRITICAL_THRESHOLD: int = 20
    LOW_THRESHOLD: int = 40
    HIGH_THRESHOLD: int = 70

    # Recovery amounts
    FOOD_RECOVERY: float = 40.0
    WATER_RECOVERY: float = 50.0
    SLEEP_RECOVERY_PER_HOUR: float = 20.0
    PLAY_HAPPINESS_BOOST: float = 15.0
    SOCIAL_HAPPINESS_BOOST: float = 10.0


@dataclass(frozen=True)
class BreedingConfig:
    """Configuration for breeding mechanics."""
    MIN_HAPPINESS_TO_BREED: int = 70
    MIN_AGE_DAYS: int = 3  # Must be adult
    MAX_AGE_DAYS: int = 30  # Seniors can't breed
    GESTATION_DAYS: int = 3
    MIN_LITTER_SIZE: int = 1
    MAX_LITTER_SIZE: int = 4
    RECOVERY_DAYS: int = 2  # Before female can breed again


@dataclass(frozen=True)
class TimeConfig:
    """Time system configuration."""
    # 1 real second = 1 game minute at 1x speed
    REAL_SECONDS_PER_GAME_MINUTE: float = 1.0
    GAME_MINUTES_PER_HOUR: int = 60
    GAME_HOURS_PER_DAY: int = 24

    # Offline limits
    MAX_OFFLINE_HOURS: int = 24

    # Day/night
    DAY_START_HOUR: int = 6
    NIGHT_START_HOUR: int = 20


@dataclass(frozen=True)
class FarmTier:
    """Farm expansion tier definition."""
    name: str
    width: int
    height: int
    capacity: int
    cost: int
    tier: int


# Farm expansion tiers
FARM_TIERS: list[FarmTier] = [
    FarmTier("Starter Hutch", 30, 15, 4, 0, 1),
    FarmTier("Cozy Enclosure", 40, 20, 12, 500, 2),
    FarmTier("Family Pen", 50, 25, 20, 2000, 3),
    FarmTier("Guinea Grove", 60, 30, 35, 8000, 4),
    FarmTier("Piggy Paradise", 80, 40, 55, 25000, 5),
    FarmTier("Ultimate Farm", 100, 50, 80, 100000, 6),
]


@dataclass(frozen=True)
class EconomyConfig:
    """Economy balance configuration."""
    STARTING_MONEY: int = 100
    STARTING_PIGS: int = 2

    # Base sale values
    COMMON_PIG_VALUE: int = 25
    UNCOMMON_MULTIPLIER: float = 1.5
    RARE_MULTIPLIER: float = 2.5
    VERY_RARE_MULTIPLIER: float = 4.0
    LEGENDARY_MULTIPLIER: float = 10.0

    # Facility costs
    FOOD_BOWL_COST: int = 20
    WATER_BOTTLE_COST: int = 20
    HAY_RACK_COST: int = 40
    HIDEOUT_COST: int = 60
    EXERCISE_WHEEL_COST: int = 80
    TUNNEL_COST: int = 100
    PLAY_AREA_COST: int = 150
    BREEDING_DEN_COST: int = 200
    NURSERY_COST: int = 250
    VEGGIE_GARDEN_COST: int = 300
    GROOMING_STATION_COST: int = 150


@dataclass(frozen=True)
class SimulationConfig:
    """Core simulation configuration."""
    # Tick rate
    TICKS_PER_SECOND: int = 10

    # Movement
    BASE_MOVE_SPEED: float = 1.0  # Cells per game minute

    # Pathfinding
    MAX_PATHFINDING_ITERATIONS: int = 1000

    # Behavior
    DECISION_INTERVAL_SECONDS: float = 2.0

    # Ages (in game days)
    BABY_AGE_DAYS: int = 0
    ADULT_AGE_DAYS: int = 3
    SENIOR_AGE_DAYS: int = 30
    MAX_AGE_DAYS: int = 45


# Singleton instances
NEEDS = NeedsConfig()
BREEDING = BreedingConfig()
TIME = TimeConfig()
ECONOMY = EconomyConfig()
SIMULATION = SimulationConfig()
