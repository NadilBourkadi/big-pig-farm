"""Facility definitions for the farm."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class FacilityType(str, Enum):
    """Types of facilities that can be built."""
    FOOD_BOWL = "food_bowl"
    WATER_BOTTLE = "water_bottle"
    HAY_RACK = "hay_rack"
    HIDEOUT = "hideout"
    EXERCISE_WHEEL = "exercise_wheel"
    TUNNEL = "tunnel"
    PLAY_AREA = "play_area"
    BREEDING_DEN = "breeding_den"
    NURSERY = "nursery"
    VEGGIE_GARDEN = "veggie_garden"
    GROOMING_STATION = "grooming_station"
    GENETICS_LAB = "genetics_lab"

    @property
    def display_name(self) -> str:
        """Human-readable name for the facility type."""
        return self.value.replace("_", " ").title()


class FacilitySize(BaseModel):
    """Size of a facility in grid cells."""
    width: int = 1
    height: int = 1


@dataclass
class FacilityInfo:
    """Typed metadata for a facility type."""
    name: str
    size: FacilitySize
    base_cost: int
    description: str
    capacity: int = 100
    refill_cost: int = 0
    health_bonus: float = 0.0
    happiness_bonus: float = 0.0
    social_bonus: float = 0.0
    breeding_bonus: float = 0.0
    growth_bonus: float = 0.0
    sale_bonus: float = 0.0
    food_production: int = 0



# Facility metadata
FACILITY_INFO: dict[FacilityType, FacilityInfo] = {
    FacilityType.FOOD_BOWL: FacilityInfo(
        name="Food Bowl",
        size=FacilitySize(width=2, height=1),
        base_cost=20,
        description="Provides food to reduce hunger",
        capacity=200,
        refill_cost=5,
    ),
    FacilityType.WATER_BOTTLE: FacilityInfo(
        name="Water Bottle",
        size=FacilitySize(width=1, height=2),
        base_cost=20,
        description="Provides water for hydration",
        capacity=200,
        refill_cost=2,
    ),
    FacilityType.HAY_RACK: FacilityInfo(
        name="Hay Rack",
        size=FacilitySize(width=2, height=1),
        base_cost=40,
        description="Fiber source, +5% health bonus",
        capacity=200,
        health_bonus=0.05,
    ),
    FacilityType.HIDEOUT: FacilityInfo(
        name="Hideout",
        size=FacilitySize(width=3, height=2),
        base_cost=60,
        description="Sleep and shelter, +10% happiness",
        capacity=2,
        happiness_bonus=0.10,
    ),
    FacilityType.EXERCISE_WHEEL: FacilityInfo(
        name="Exercise Wheel",
        size=FacilitySize(width=2, height=2),
        base_cost=80,
        description="Entertainment and fitness, +5% health",
        health_bonus=0.05,
    ),
    FacilityType.TUNNEL: FacilityInfo(
        name="Tunnel System",
        size=FacilitySize(width=3, height=1),
        base_cost=100,
        description="Exploration and play, +15% happiness",
        happiness_bonus=0.15,
    ),
    FacilityType.PLAY_AREA: FacilityInfo(
        name="Play Area",
        size=FacilitySize(width=3, height=2),
        base_cost=150,
        description="Social activities, +social chance",
        social_bonus=0.20,
    ),
    FacilityType.BREEDING_DEN: FacilityInfo(
        name="Breeding Den",
        size=FacilitySize(width=2, height=2),
        base_cost=200,
        description="Private space for mating",
        breeding_bonus=0.15,
    ),
    FacilityType.NURSERY: FacilityInfo(
        name="Nursery",
        size=FacilitySize(width=3, height=2),
        base_cost=250,
        description="Baby care, faster growth",
        growth_bonus=0.20,
        capacity=4,
    ),
    FacilityType.VEGGIE_GARDEN: FacilityInfo(
        name="Veggie Garden",
        size=FacilitySize(width=2, height=2),
        base_cost=300,
        description="Grows fresh vegetables",
        food_production=10,
    ),
    FacilityType.GROOMING_STATION: FacilityInfo(
        name="Grooming Station",
        size=FacilitySize(width=2, height=1),
        base_cost=150,
        description="Health and appearance, +15% sale value",
        sale_bonus=0.15,
    ),
    FacilityType.GENETICS_LAB: FacilityInfo(
        name="Genetics Lab",
        size=FacilitySize(width=3, height=2),
        base_cost=350,
        description="Reveals carrier alleles and boosts mutation rate",
    ),
}


class Facility(BaseModel):
    """A facility placed on the farm."""
    id: UUID = Field(default_factory=uuid4)
    facility_type: FacilityType
    position_x: int
    position_y: int
    level: int = 1
    max_level: int = 3

    # Resource state (for consumable facilities)
    current_amount: float = 100.0
    max_amount: float = 100.0

    # Auto-refill setting
    auto_refill: bool = False

    # Area tracking — auto-assigned on placement based on position
    area_id: Optional[UUID] = None

    @property
    def info(self) -> FacilityInfo:
        """Get facility metadata."""
        return FACILITY_INFO[self.facility_type]

    @property
    def name(self) -> str:
        """Get facility display name."""
        return self.info.name

    @property
    def size(self) -> FacilitySize:
        """Get facility size."""
        return self.info.size

    @property
    def width(self) -> int:
        """Get facility width in cells."""
        return self.size.width

    @property
    def height(self) -> int:
        """Get facility height in cells."""
        return self.size.height

    @property
    def cells(self) -> list[tuple[int, int]]:
        """Get all cells occupied by this facility."""
        cells = []
        for dx in range(self.width):
            for dy in range(self.height):
                cells.append((self.position_x + dx, self.position_y + dy))
        return cells

    @property
    def interaction_point(self) -> tuple[int, int]:
        """Get the primary cell where guinea pigs interact with this facility."""
        # Usually the front-center of the facility
        return (self.position_x + self.width // 2, self.position_y + self.height)

    @property
    def interaction_points(self) -> list[tuple[int, int]]:
        """Get all valid cells where guinea pigs can interact with this facility.

        Returns cells along the front and sides of the facility, filtering out
        any cells with negative coordinates (which would be out of bounds).
        Computed once on first access (facilities are immutable once placed).
        """
        cached = getattr(self, "_interaction_points_cache", None)
        if cached is not None:
            return cached
        points = []
        # Add cells along the front (bottom) of the facility
        for dx in range(self.width):
            x, y = self.position_x + dx, self.position_y + self.height
            if x >= 0 and y >= 0:
                points.append((x, y))
        # Add cells along the sides
        for dy in range(self.height):
            # Left side
            x, y = self.position_x - 1, self.position_y + dy
            if x >= 0 and y >= 0:
                points.append((x, y))
            # Right side
            x, y = self.position_x + self.width, self.position_y + dy
            if x >= 0 and y >= 0:
                points.append((x, y))
        object.__setattr__(self, "_interaction_points_cache", points)
        return points

    def clear_interaction_points_cache(self) -> None:
        """Clear cached interaction points (call after repositioning)."""
        try:
            object.__delattr__(self, "_interaction_points_cache")
        except AttributeError:
            pass

    @property
    def is_empty(self) -> bool:
        """Check if facility has no resources left."""
        return self.current_amount <= 0

    @property
    def fill_percentage(self) -> float:
        """Get fill percentage for display."""
        if self.max_amount <= 0:
            return 100.0
        return (self.current_amount / self.max_amount) * 100

    def consume(self, amount: float) -> float:
        """Consume resources from this facility. Returns amount actually consumed."""
        actual = min(amount, self.current_amount)
        self.current_amount -= actual
        return actual

    def refill(self, amount: Optional[float] = None) -> None:
        """Refill the facility."""
        # Always sync max_amount with configured capacity
        configured_capacity = self.info.capacity
        if self.max_amount != configured_capacity:
            self.max_amount = configured_capacity

        if amount is None:
            self.current_amount = self.max_amount
        else:
            self.current_amount = min(self.max_amount, self.current_amount + amount)

    def upgrade(self) -> bool:
        """Upgrade the facility to next level. Returns True if successful."""
        if self.level >= self.max_level:
            return False
        self.level += 1
        # Increase capacity with level
        self.max_amount *= 1.5
        return True

    def get_upgrade_cost(self) -> int:
        """Calculate cost to upgrade to next level."""
        if self.level >= self.max_level:
            return 0
        base = self.info.base_cost
        return int(base * (self.level + 1) * 0.75)

    @classmethod
    def create(
        cls,
        facility_type: FacilityType,
        x: int,
        y: int,
    ) -> "Facility":
        """Create a new facility at the given position."""
        info = FACILITY_INFO[facility_type]
        capacity = info.capacity

        return cls(
            facility_type=facility_type,
            position_x=x,
            position_y=y,
            current_amount=capacity,
            max_amount=capacity,
        )
