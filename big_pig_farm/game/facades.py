"""Domain-specific facades that limit access to GameState.

These thin wrappers restrict what each subsystem can see and mutate,
making dependencies explicit. Modules can be migrated to facades
gradually — GameState remains unchanged.
"""

from typing import Optional
from uuid import UUID

from big_pig_farm.entities.guinea_pig import GuineaPig
from big_pig_farm.entities.facilities import Facility


class EconomyFacade:
    """Read/write access to money and event logging only."""

    def __init__(self, state):
        self._state = state

    @property
    def money(self) -> int:
        return self._state.money

    def add_money(self, amount: int) -> None:
        self._state.add_money(amount)

    def spend_money(self, amount: int) -> bool:
        return self._state.spend_money(amount)

    def log_event(self, message: str, event_type: str = "info") -> None:
        self._state.log_event(message, event_type)


class PopulationFacade:
    """Read/write access to pigs and facilities."""

    def __init__(self, state):
        self._state = state

    @property
    def farm(self):
        return self._state.farm

    @property
    def pig_count(self) -> int:
        return self._state.pig_count

    @property
    def capacity(self) -> int:
        return self._state.capacity

    def get_pigs_list(self) -> list[GuineaPig]:
        return self._state.get_pigs_list()

    def get_guinea_pig(self, pig_id: UUID) -> Optional[GuineaPig]:
        return self._state.get_guinea_pig(pig_id)

    def add_guinea_pig(self, pig: GuineaPig) -> None:
        self._state.add_guinea_pig(pig)

    def remove_guinea_pig(self, pig_id: UUID) -> Optional[GuineaPig]:
        return self._state.remove_guinea_pig(pig_id)

    def get_facilities_list(self) -> list[Facility]:
        return self._state.get_facilities_list()

    def get_facilities_by_type(self, facility_type) -> list[Facility]:
        return self._state.get_facilities_by_type(facility_type)

    def get_facility(self, facility_id: UUID) -> Optional[Facility]:
        return self._state.get_facility(facility_id)

    def add_facility(self, facility: Facility) -> bool:
        return self._state.add_facility(facility)

    def remove_facility(self, facility_id: UUID) -> Optional[Facility]:
        return self._state.remove_facility(facility_id)

    def log_event(self, message: str, event_type: str = "info") -> None:
        self._state.log_event(message, event_type)


class BreedingFacade:  # TODO: wire into breeding callers
    """Read/write access to breeding-related state."""

    def __init__(self, state):
        self._state = state

    @property
    def pigdex(self):
        return self._state.pigdex

    @property
    def breeding_program(self):
        return self._state.breeding_program

    @property
    def breeding_pair(self):
        return self._state.breeding_pair

    @breeding_pair.setter
    def breeding_pair(self, value):
        self._state.breeding_pair = value

    @property
    def contract_board(self):
        return self._state.contract_board

    def log_event(self, message: str, event_type: str = "info") -> None:
        self._state.log_event(message, event_type)
