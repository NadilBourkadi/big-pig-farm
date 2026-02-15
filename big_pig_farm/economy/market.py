"""Guinea pig valuation and selling.

Functions accept GameState directly. Domain facades (EconomyFacade,
PopulationFacade) can be used by future callers — the duck-typed
interface is compatible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Union

from big_pig_farm.data.config import ECONOMY
from big_pig_farm.economy.currency import add_money
from big_pig_farm.entities.guinea_pig import GuineaPig
from big_pig_farm.entities.genetics import Rarity
from big_pig_farm.entities.facilities import FacilityType
from big_pig_farm.game.state import GameState

if TYPE_CHECKING:
    from big_pig_farm.game.facades import PopulationFacade


@dataclass
class SaleResult:
    """Result of selling a guinea pig."""
    base_value: int
    contract_bonus: int
    matched_contract: Optional[object]

    @property
    def total(self) -> int:
        return self.base_value + self.contract_bonus


def get_rarity_multiplier(rarity: Rarity) -> float:
    """Get the price multiplier for a given rarity."""
    multipliers = {
        Rarity.COMMON: 1.0,
        Rarity.UNCOMMON: ECONOMY.UNCOMMON_MULTIPLIER,
        Rarity.RARE: ECONOMY.RARE_MULTIPLIER,
        Rarity.VERY_RARE: ECONOMY.VERY_RARE_MULTIPLIER,
        Rarity.LEGENDARY: ECONOMY.LEGENDARY_MULTIPLIER,
    }
    return multipliers.get(rarity, 1.0)


def calculate_pig_value(pig: GuineaPig, state: Optional[Union[GameState, PopulationFacade]] = None) -> int:
    """Calculate the sale value of a guinea pig."""
    return calculate_pig_value_breakdown(pig, state)["total"]


def calculate_pig_value_breakdown(pig: GuineaPig, state: Optional[Union[GameState, PopulationFacade]] = None) -> dict:
    """Calculate sale value with individual multiplier breakdown.

    Returns dict with: base, rarity_mult, age_mult, health_mult, grooming_mult, total
    """
    base_value = ECONOMY.COMMON_PIG_VALUE
    rarity_mult = get_rarity_multiplier(pig.phenotype.rarity)

    if pig.is_baby:
        age_mult = 0.5
    elif pig.is_senior:
        age_mult = 0.8
    else:
        age_mult = 1.0

    health_mult = pig.needs.health / 100.0
    if health_mult < 0.5:
        health_mult = 0.5

    grooming_mult = 1.0
    if state:
        grooming_stations = state.get_facilities_by_type(FacilityType.GROOMING_STATION)
        if grooming_stations:
            grooming_mult = 1.15

    total = base_value * rarity_mult * age_mult * health_mult * grooming_mult

    return {
        "base": base_value,
        "rarity_mult": rarity_mult,
        "age_mult": age_mult,
        "health_mult": health_mult,
        "grooming_mult": grooming_mult,
        "total": max(1, int(total)),
    }


def sell_pig(state: GameState, pig: GuineaPig) -> SaleResult:
    """Sell a guinea pig. Returns a SaleResult with value breakdown."""
    value = calculate_pig_value(pig, state)

    # Check for contract fulfillment
    contract_bonus = 0
    matched_contract = state.contract_board.check_and_fulfill(pig, farm=state.farm)
    if matched_contract:
        contract_bonus = matched_contract.reward
        state.contract_board.remove_fulfilled()

    result = SaleResult(
        base_value=value,
        contract_bonus=contract_bonus,
        matched_contract=matched_contract,
    )

    # Remove pig from game
    state.remove_guinea_pig(pig.id)
    state.total_pigs_sold += 1

    # Add money
    add_money(state, result.total, f"Sold {pig.name}")

    # Log event
    if contract_bonus > 0:
        state.log_event(
            f"Rehomed {pig.name} ({pig.phenotype.display_name}) for {value} + {contract_bonus} contract bonus = {result.total} Squeaks",
            event_type="sale",
        )
        state.log_event(
            f"Contract fulfilled: \"{matched_contract.description}\" (+{contract_bonus} bonus)",
            event_type="contract",
        )
    else:
        state.log_event(
            f"Rehomed {pig.name} ({pig.phenotype.display_name}) for {value} Squeaks",
            event_type="sale",
        )

    return result


def get_market_info(state: GameState) -> dict:
    """Get current market information."""
    pigs = state.get_pigs_list()

    # Calculate total farm value
    total_value = sum(calculate_pig_value(p, state) for p in pigs)

    # Count by rarity
    rarity_counts = {}
    for pig in pigs:
        rarity = pig.phenotype.rarity.value
        rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1

    # Most valuable pig
    most_valuable = max(pigs, key=lambda p: calculate_pig_value(p, state)) if pigs else None

    return {
        "total_value": total_value,
        "pig_count": len(pigs),
        "rarity_counts": rarity_counts,
        "most_valuable": most_valuable,
        "most_valuable_price": calculate_pig_value(most_valuable, state) if most_valuable else 0,
    }
