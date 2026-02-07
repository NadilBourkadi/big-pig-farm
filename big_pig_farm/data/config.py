"""Game balance constants and configuration."""

from dataclasses import dataclass
from enum import Enum


class GameSpeed(Enum):
    """Game speed multipliers."""
    PAUSED = 0
    NORMAL = 3
    FAST = 6
    FASTER = 15
    FASTEST = 60


# Display labels for speed (decoupled from internal multiplier)
SPEED_DISPLAY: dict["GameSpeed", str] = {}  # Populated after enum definition


def _init_speed_display() -> None:
    SPEED_DISPLAY[GameSpeed.PAUSED] = "0x"
    SPEED_DISPLAY[GameSpeed.NORMAL] = "1x"
    SPEED_DISPLAY[GameSpeed.FAST] = "2x"
    SPEED_DISPLAY[GameSpeed.FASTER] = "5x"
    SPEED_DISPLAY[GameSpeed.FASTEST] = "20x"


_init_speed_display()


@dataclass(frozen=True)
class NeedsConfig:
    """Configuration for guinea pig needs decay and thresholds."""
    # Decay rates per game hour
    HUNGER_DECAY: float = 3.5
    THIRST_DECAY: float = 4.5
    ENERGY_DECAY: float = 2.0
    HAPPINESS_BASE_DECAY: float = 2.0

    # Thresholds
    CRITICAL_THRESHOLD: int = 20
    LOW_THRESHOLD: int = 40
    HIGH_THRESHOLD: int = 70
    SATISFACTION_THRESHOLD: int = 90  # Pigs commit to an action until the need reaches this level

    # Health
    HEALTH_DRAIN_HUNGER: float = 0.3
    HEALTH_DRAIN_THIRST: float = 0.5
    HEALTH_PASSIVE_RECOVERY: float = 1.0
    HEALTH_SLEEP_RECOVERY: float = 1.5

    # Recovery amounts
    FOOD_RECOVERY: float = 40.0
    WATER_RECOVERY: float = 50.0
    SLEEP_RECOVERY_PER_HOUR: float = 25.0
    PLAY_HAPPINESS_BOOST: float = 15.0
    SOCIAL_HAPPINESS_BOOST: float = 10.0

    # Boredom
    BOREDOM_DECAY: float = 3.0                # per game hour
    BOREDOM_EXTRA_HAPPINESS_THRESHOLD: int = 70
    BOREDOM_EXTRA_HAPPINESS_DRAIN: float = 1.0
    BOREDOM_PLAY_RECOVERY: float = 15.0
    PLAY_ENERGY_COST: float = 1.0
    SOCIAL_RECOVERY: float = 10.0

    # Social
    SOCIAL_RADIUS: float = 8.0                # distance to check nearby pigs
    SOCIAL_BOOST_PER_PIG: float = 3.0         # per nearby pig (capped)
    SOCIAL_BOOST_CAP: float = 8.0
    SOCIAL_DECAY_WITH_PIGS: float = 0.5
    SOCIAL_DECAY_ALONE: float = 2.0

    # Happiness boosts during behavior
    EATING_HAPPINESS_BOOST: float = 2.0

    # Happiness multipliers when needs are critical
    HUNGER_CRITICAL_HAPPINESS_MULT: float = 1.5
    THIRST_CRITICAL_HAPPINESS_MULT: float = 1.5
    ENERGY_CRITICAL_HAPPINESS_MULT: float = 1.25

    # Personality modifiers
    GREEDY_HUNGER_MULT: float = 1.5
    LAZY_ENERGY_MULT: float = 0.7
    PLAYFUL_BOREDOM_MULT: float = 1.5
    SOCIAL_SOCIAL_MULT: float = 1.3
    SHY_SOCIAL_MULT: float = 0.5

    # Wellbeing weights
    WELLBEING_HUNGER_WEIGHT: float = 0.25
    WELLBEING_THIRST_WEIGHT: float = 0.25
    WELLBEING_ENERGY_WEIGHT: float = 0.15
    WELLBEING_HAPPINESS_WEIGHT: float = 0.20
    WELLBEING_HEALTH_WEIGHT: float = 0.15


@dataclass(frozen=True)
class BreedingConfig:
    """Configuration for breeding mechanics."""
    MIN_HAPPINESS_TO_BREED: int = 70
    MIN_AGE_DAYS: int = 3  # Must be adult
    MAX_AGE_DAYS: int = 30  # Seniors can't breed
    GESTATION_DAYS: int = 2
    MIN_LITTER_SIZE: int = 1
    MAX_LITTER_SIZE: int = 4
    RECOVERY_DAYS: int = 2  # Before female can breed again
    BREEDING_DISTANCE: float = 3.0      # Max distance for pigs to breed
    BASE_BREEDING_CHANCE: float = 0.05  # 5% per check
    BREEDING_DEN_BONUS: float = 0.10    # +10% with breeding den
    HIGH_HAPPINESS_THRESHOLD: int = 80  # Threshold for happiness breeding bonus
    HIGH_HAPPINESS_BONUS: float = 0.05  # +5% with high happiness
    OLD_AGE_DEATH_RATE: float = 0.1     # Base death rate multiplier per game day past max age


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
    GENETICS_LAB_COST: int = 350


@dataclass(frozen=True)
class BloodlineConfig:
    """Configuration for bloodline adoption pigs."""
    BLOODLINE_PIG_CHANCE: float = 0.5  # 50% of adoption pigs are bloodline carriers
    ADOPTION_REFRESH_DAYS: int = 5


@dataclass(frozen=True)
class GeneticsConfig:
    """Configuration for genetics and mutations."""
    MUTATION_RATE: float = 0.02  # 2% per locus
    MUTATION_RATE_WITH_LAB: float = 0.03  # 3% per locus with Genetics Lab


@dataclass(frozen=True)
class PigdexConfig:
    """Configuration for Pigdex rewards."""
    # Discovery rewards by rarity
    COMMON_REWARD: int = 10
    UNCOMMON_REWARD: int = 20
    RARE_REWARD: int = 35
    VERY_RARE_REWARD: int = 50
    LEGENDARY_REWARD: int = 100
    # Milestone rewards (at 25/50/75/100% completion)
    MILESTONE_25_REWARD: int = 250
    MILESTONE_50_REWARD: int = 750
    MILESTONE_75_REWARD: int = 2000
    MILESTONE_100_REWARD: int = 10000


@dataclass(frozen=True)
class ContractConfig:
    """Configuration for breeding contracts."""
    MAX_ACTIVE_CONTRACTS: int = 4
    REFRESH_INTERVAL_DAYS: int = 10
    EXPIRY_DAYS: int = 20
    # Reward ranges by difficulty
    EASY_REWARD_MIN: int = 50
    EASY_REWARD_MAX: int = 100
    MEDIUM_REWARD_MIN: int = 100
    MEDIUM_REWARD_MAX: int = 200
    HARD_REWARD_MIN: int = 200
    HARD_REWARD_MAX: int = 500
    EXPERT_REWARD_MIN: int = 500
    EXPERT_REWARD_MAX: int = 1000


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


@dataclass(frozen=True)
class BehaviorConfig:
    """Configuration for pig AI behavior decisions."""
    # Separation thresholds (must be < blocking threshold for same state)
    SEPARATION_BOTH_MOVING: float = 1.0   # Both pigs moving
    SEPARATION_ONE_MOVING: float = 2.0    # One pig moving
    MIN_PIG_DISTANCE: float = 3.0         # Both stationary

    # Movement blocking distances
    BLOCKING_DEFAULT: float = 2.5         # Default (stationary blocks moving)
    BLOCKING_BOTH_MOVING: float = 1.5     # Both pigs have active paths
    BLOCKING_FACILITY_USE: float = 1.5    # Reduced blocking for pigs actively using a facility

    # Facility co-use separation
    SEPARATION_FACILITY_USE: float = 1.0  # Reduced separation for co-located facility users

    # Facility interaction
    OCCUPANCY_RADIUS: float = 2.0         # Distance to check facility occupancy
    FACILITY_NEARBY_RADIUS: float = 6.0   # Distance for counting nearby pigs
    FACILITY_HEADING_RADIUS: float = 3.0  # Distance for counting pigs heading to facility
    CROWDING_PENALTY: float = 25.0        # Scoring penalty per nearby pig
    SCORING_RANDOM_VARIANCE: float = 3.0  # Random variance in facility scoring
    UNCROWDED_CHANCE: float = 0.3         # Chance to prioritize uncrowded facility

    # Blocked behavior
    BLOCKED_TIME_ALTERNATIVE: float = 2.0  # Seconds blocked before trying alternative
    BLOCKED_TIME_GIVE_UP: float = 5.0      # Seconds blocked before giving up
    FAILED_COOLDOWN_CYCLES: int = 3        # Decision cycles to preserve failed list

    # Decision thresholds
    ENERGY_SLEEP_THRESHOLD: int = 30       # Energy level to seek sleep
    EMERGENCY_WAKE_ENERGY: int = 15        # Min energy to wake from sleep for critical need
    BOREDOM_PLAY_THRESHOLD: int = 30       # Boredom level to seek play
    BOREDOM_KEEP_PLAYING: int = 10         # Boredom level to keep playing

    # Resource consumption
    RESOURCE_CONSUME_RATE: float = 0.5     # Rate of consuming facility resources
    FACILITY_BONUS_SCALE: float = 10.0     # Scaling factor for facility bonuses

    # Personality behavior probabilities
    LAZY_SLEEP_CHANCE: float = 0.3
    PLAYFUL_PLAY_CHANCE: float = 0.4
    SOCIAL_SOCIALIZE_CHANCE: float = 0.3
    WANDER_CHANCE: float = 0.8             # Wander vs idle when nothing to do
    NO_PLAY_FACILITY_PLAY_CHANCE: float = 0.5  # Play vs wander when no facility

    # Wandering
    WANDER_ATTEMPTS: int = 20              # Random positions to try when wandering
    WANDER_PIG_DISTANCE_WEIGHT: float = 0.5  # Weight of min pig distance in scoring

    # Movement modifiers
    TIRED_SPEED_MULT: float = 0.5          # Speed when energy < sleep threshold
    BABY_SPEED_MULT: float = 0.7
    DODGE_MAX_STEP: float = 1.0            # Max dodge step distance
    WAYPOINT_REACHED: float = 0.1          # Distance to consider a waypoint reached

    # Overlap handling
    OVERLAP_EPSILON: float = 0.01          # Minimum distance before treating as zero
    SEPARATION_PADDING: float = 0.1        # Extra padding when separating
    PATH_VECTOR_EPSILON: float = 0.01      # Min path vector magnitude


@dataclass(frozen=True)
class FacilityInteractionConfig:
    """Configuration for facility adjacency checks."""
    ADJACENCY_DISTANCE: int = 1  # Orthogonal adjacency for facility arrival/consumption
    DEFAULT_HIDEOUT_CAPACITY: int = 2


# Singleton instances
NEEDS = NeedsConfig()
BREEDING = BreedingConfig()
TIME = TimeConfig()
ECONOMY = EconomyConfig()
SIMULATION = SimulationConfig()
BLOODLINE = BloodlineConfig()
GENETICS = GeneticsConfig()
PIGDEX = PigdexConfig()
CONTRACTS = ContractConfig()
BEHAVIOR = BehaviorConfig()
FACILITY_INTERACTION = FacilityInteractionConfig()
