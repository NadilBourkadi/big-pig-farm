"""Guinea pig valuation and selling."""

from typing import Optional

from big_pig_farm.data.config import ECONOMY
from big_pig_farm.economy.currency import add_money
from big_pig_farm.entities.guinea_pig import GuineaPig
from big_pig_farm.entities.genetics import Rarity
from big_pig_farm.entities.facilities import FacilityType
from big_pig_farm.game.state import GameState


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


def calculate_pig_value(pig: GuineaPig, state: Optional[GameState] = None) -> int:
    """Calculate the sale value of a guinea pig."""
    base_value = ECONOMY.COMMON_PIG_VALUE

    # Rarity multiplier
    rarity_mult = get_rarity_multiplier(pig.phenotype.rarity)

    # Age modifier (babies worth less, adults full value, seniors slightly less)
    if pig.is_baby:
        age_mult = 0.5
    elif pig.is_senior:
        age_mult = 0.8
    else:
        age_mult = 1.0

    # Health modifier
    health_mult = pig.needs.health / 100.0
    if health_mult < 0.5:
        health_mult = 0.5  # Minimum 50% value

    # Grooming station bonus
    grooming_mult = 1.0
    if state:
        grooming_stations = state.get_facilities_by_type(FacilityType.GROOMING_STATION)
        if grooming_stations:
            grooming_mult = 1.15  # +15% from grooming

    total = base_value * rarity_mult * age_mult * health_mult * grooming_mult
    return max(1, int(total))


def sell_pig(state: GameState, pig: GuineaPig) -> int:
    """Sell a guinea pig. Returns the total sale price (including contract bonus)."""
    value = calculate_pig_value(pig, state)

    # Check for contract fulfillment
    contract_bonus = 0
    matched_contract = state.contract_board.check_and_fulfill(pig)
    if matched_contract:
        contract_bonus = matched_contract.reward
        state.contract_board.remove_fulfilled()

    total = value + contract_bonus

    # Remove pig from game
    state.remove_guinea_pig(pig.id)
    state.total_pigs_sold += 1

    # Add money
    add_money(state, total, f"Sold {pig.name}")

    # Log event
    if contract_bonus > 0:
        state.log_event(
            f"Rehomed {pig.name} ({pig.phenotype.display_name}) for {value} + {contract_bonus} contract bonus = {total} Squeaks",
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

    return total


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
