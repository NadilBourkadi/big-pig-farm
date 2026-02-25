"""Adoption utilities for generating and pricing guinea pigs."""

import random
from typing import TYPE_CHECKING

from big_pig_farm.data.config import BLOODLINE
from big_pig_farm.data.names import generate_unique_name
from big_pig_farm.economy.market import get_rarity_multiplier
from big_pig_farm.entities.bloodlines import (
    BLOODLINES,
    generate_bloodline_pig_genotype,
    pick_random_bloodline,
)
from big_pig_farm.entities.guinea_pig import Gender, GuineaPig

if TYPE_CHECKING:
    from big_pig_farm.game.state import GameState


# Adoption costs are higher than sale prices to prevent buy/sell exploits
ADOPTION_BASE_COST = 50  # Common pigs cost 50 (sell for 25)


def calculate_adoption_cost(pig: GuineaPig, state: "GameState | None" = None) -> int:
    """Calculate the adoption cost for a guinea pig.

    Bloodline pigs have their cost multiplied by the bloodline cost_multiplier
    (applied on top of rarity multiplier).
    """
    multiplier = get_rarity_multiplier(pig.phenotype.rarity)
    base_cost = int(ADOPTION_BASE_COST * multiplier)

    # Bloodline pigs cost more based on their bloodline
    if pig.origin_tag:
        for bloodline in BLOODLINES.values():
            if bloodline.display_name == pig.origin_tag:
                base_cost = int(base_cost * bloodline.cost_multiplier)
                break

    # Adoption Discount perk: -15% adoption cost
    if state and state.has_upgrade("adoption_discount"):
        base_cost = int(base_cost * 0.85)

    return base_cost


def generate_adoption_pig(existing_names: set[str], farm_tier: int = 1) -> GuineaPig:
    """Generate a random guinea pig available for adoption.

    About 50% of generated pigs are bloodline carriers (filtered by farm tier).
    """
    gender = random.choice([Gender.MALE, Gender.FEMALE])
    name = generate_unique_name(existing_names, gender=gender.value)

    # Chance to generate a bloodline carrier pig
    origin_tag = None
    genotype = None
    if random.random() < BLOODLINE.BLOODLINE_PIG_CHANCE:
        bloodline = pick_random_bloodline(farm_tier)
        if bloodline:
            genotype = generate_bloodline_pig_genotype(bloodline)
            origin_tag = bloodline.display_name

    # Create an adult pig (age 5 days) with random genetics
    pig = GuineaPig.create(
        name=name,
        gender=gender,
        genotype=genotype,
        age_days=5.0,  # Adults ready for adoption
    )
    pig.origin_tag = origin_tag
    return pig
