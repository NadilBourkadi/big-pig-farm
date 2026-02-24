"""Protocol interfaces for simulation subsystem dependencies.

Each Protocol defines the narrowest view of GameState that a subsystem needs.
GameState satisfies all Protocols implicitly — no wrapper classes needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from big_pig_farm.economy.contracts import ContractBoard
    from big_pig_farm.entities.facilities import Facility, FacilityType
    from big_pig_farm.entities.guinea_pig import GuineaPig
    from big_pig_farm.entities.pigdex import Pigdex
    from big_pig_farm.game.state import BreedingPair, GameTime
    from big_pig_farm.game.world import FarmGrid
    from big_pig_farm.simulation.breeding_program import BreedingProgram


@runtime_checkable
class NeedsContext(Protocol):
    """Used by simulation/needs.py — read-only pig/biome access."""

    farm: FarmGrid

    def get_pigs_list(self) -> list[GuineaPig]: ...


@runtime_checkable
class BreedingContext(Protocol):
    """Used by simulation/breeding.py — breeding pair management."""

    breeding_pair: BreedingPair | None
    breeding_program: BreedingProgram
    contract_board: ContractBoard
    game_time: GameTime
    is_at_capacity: bool

    def clear_breeding_pair(self) -> None: ...
    def get_affinity(self, id1: UUID, id2: UUID) -> int: ...
    def get_facilities_by_type(self, facility_type: FacilityType) -> list[Facility]: ...
    def get_guinea_pig(self, pig_id: UUID) -> GuineaPig | None: ...
    def get_pigs_list(self) -> list[GuineaPig]: ...
    def log_event(self, message: str, event_type: str = "info") -> None: ...
    def set_breeding_pair(self, male_id: UUID, female_id: UUID) -> None: ...


@runtime_checkable
class BirthContext(Protocol):
    """Used by simulation/birth.py — birth processing, aging, pigdex."""

    breeding_program: BreedingProgram
    capacity: int
    farm: FarmGrid
    game_time: GameTime
    is_at_capacity: bool
    pig_count: int
    pigdex: Pigdex
    total_pigs_born: int

    def add_guinea_pig(self, pig: GuineaPig) -> None: ...
    def add_money(self, amount: int) -> None: ...
    def get_facilities_by_type(self, facility_type: FacilityType) -> list[Facility]: ...
    def get_guinea_pig(self, pig_id: UUID) -> GuineaPig | None: ...
    def get_pigs_list(self) -> list[GuineaPig]: ...
    def log_event(self, message: str, event_type: str = "info") -> None: ...
    def remove_guinea_pig(self, pig_id: UUID) -> GuineaPig | None: ...


@runtime_checkable
class CullingContext(Protocol):
    """Used by simulation/culling.py — surplus management."""

    breeding_program: BreedingProgram
    contract_board: ContractBoard

    def get_facilities_by_type(self, facility_type: FacilityType) -> list[Facility]: ...
    def get_pigs_list(self) -> list[GuineaPig]: ...
    def log_event(self, message: str, event_type: str = "info") -> None: ...
