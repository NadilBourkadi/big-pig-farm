"""Game state container - holds all game data."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from big_pig_farm.data.config import ECONOMY, GameSpeed
from big_pig_farm.entities.guinea_pig import GuineaPig
from big_pig_farm.entities.facilities import Facility
from big_pig_farm.entities.pigdex import Pigdex
from big_pig_farm.economy.contracts import ContractBoard
from big_pig_farm.simulation.breeding_program import BreedingProgram
from big_pig_farm.game.world import FarmGrid


class GameTime(BaseModel):
    """Tracks game time progression."""
    day: int = 1
    hour: int = 8  # Start at 8 AM
    minute: int = 0

    # Real-world tracking
    last_update: datetime = Field(default_factory=datetime.now)
    total_game_minutes: float = 0.0

    @property
    def is_daytime(self) -> bool:
        """Check if it's currently daytime (6 AM - 8 PM)."""
        return 6 <= self.hour < 20

    @property
    def time_of_day(self) -> str:
        """Get description of time of day."""
        if 6 <= self.hour < 12:
            return "Morning"
        elif 12 <= self.hour < 17:
            return "Afternoon"
        elif 17 <= self.hour < 20:
            return "Evening"
        else:
            return "Night"

    @property
    def display_time(self) -> str:
        """Get formatted time string."""
        period = "AM" if self.hour < 12 else "PM"
        display_hour = self.hour % 12 or 12
        return f"{display_hour}:{self.minute:02d} {period}"

    def advance(self, minutes: float) -> None:
        """Advance game time by the given number of minutes."""
        self.total_game_minutes += minutes
        self.minute += int(minutes)

        while self.minute >= 60:
            self.minute -= 60
            self.hour += 1

        while self.hour >= 24:
            self.hour -= 24
            self.day += 1


class EventLog(BaseModel):
    """A logged game event."""
    timestamp: datetime = Field(default_factory=datetime.now)
    game_day: int = 1
    message: str
    event_type: str = "info"  # info, birth, death, sale, purchase


class BreedingPair(BaseModel):
    """A manually set breeding pair."""
    male_id: UUID
    female_id: UUID


class GameState(BaseModel):
    """Complete game state."""
    # Core collections
    guinea_pigs: dict[UUID, GuineaPig] = Field(default_factory=dict)
    facilities: dict[UUID, Facility] = Field(default_factory=dict)

    # World
    farm: FarmGrid = Field(default_factory=FarmGrid.create_starter)

    # Economy
    money: int = ECONOMY.STARTING_MONEY

    # Time
    game_time: GameTime = Field(default_factory=GameTime)
    speed: GameSpeed = GameSpeed.NORMAL
    is_paused: bool = False

    # Session tracking
    session_start: datetime = Field(default_factory=datetime.now)
    last_save: Optional[datetime] = None

    # Event log (recent events for display)
    events: list[EventLog] = Field(default_factory=list)
    max_events: int = 100

    # Collections
    pigdex: Pigdex = Field(default_factory=Pigdex)
    contract_board: ContractBoard = Field(default_factory=ContractBoard)

    # Breeding program
    breeding_program: BreedingProgram = Field(default_factory=BreedingProgram)

    # Manual breeding
    breeding_pair: Optional[BreedingPair] = None

    # Statistics
    total_pigs_born: int = 0
    total_pigs_sold: int = 0
    total_earnings: int = 0

    def add_guinea_pig(self, pig: GuineaPig) -> None:
        """Add a guinea pig to the game."""
        self.guinea_pigs[pig.id] = pig

    def remove_guinea_pig(self, pig_id: UUID) -> Optional[GuineaPig]:
        """Remove and return a guinea pig from the game."""
        return self.guinea_pigs.pop(pig_id, None)

    def get_guinea_pig(self, pig_id: UUID) -> Optional[GuineaPig]:
        """Get a guinea pig by ID."""
        return self.guinea_pigs.get(pig_id)

    def add_facility(self, facility: Facility) -> bool:
        """Add a facility to the game and place it on the grid."""
        if self.farm.place_facility(facility):
            self.facilities[facility.id] = facility
            return True
        return False

    def remove_facility(self, facility_id: UUID) -> Optional[Facility]:
        """Remove a facility from the game."""
        facility = self.facilities.pop(facility_id, None)
        if facility:
            self.farm.remove_facility(facility)
        return facility

    def get_facility(self, facility_id: UUID) -> Optional[Facility]:
        """Get a facility by ID."""
        return self.facilities.get(facility_id)

    def get_facilities_by_type(self, facility_type) -> list[Facility]:
        """Get all facilities of a specific type."""
        return [f for f in self.facilities.values() if f.facility_type == facility_type]

    def add_money(self, amount: int) -> None:
        """Add money to the player's balance."""
        self.money += amount
        if amount > 0:
            self.total_earnings += amount

    def spend_money(self, amount: int) -> bool:
        """Spend money if available. Returns True if successful."""
        if self.money >= amount:
            self.money -= amount
            return True
        return False

    def log_event(self, message: str, event_type: str = "info") -> None:
        """Log a game event."""
        event = EventLog(
            game_day=self.game_time.day,
            message=message,
            event_type=event_type,
        )
        self.events.append(event)

        # Trim old events
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

    @property
    def pig_count(self) -> int:
        """Get current number of guinea pigs."""
        return len(self.guinea_pigs)

    @property
    def capacity(self) -> int:
        """Get farm capacity."""
        return self.farm.capacity

    @property
    def is_at_capacity(self) -> bool:
        """Check if farm is at maximum capacity."""
        return self.pig_count >= self.capacity

    def set_breeding_pair(self, male_id: UUID, female_id: UUID) -> None:
        """Set a manual breeding pair."""
        self.breeding_pair = BreedingPair(male_id=male_id, female_id=female_id)

    def clear_breeding_pair(self) -> None:
        """Clear the manual breeding pair."""
        self.breeding_pair = None

    def get_pigs_list(self) -> list[GuineaPig]:
        """Get all guinea pigs as a list."""
        return list(self.guinea_pigs.values())

    def get_facilities_list(self) -> list[Facility]:
        """Get all facilities as a list."""
        return list(self.facilities.values())
