"""Shop items and pricing."""

from dataclasses import dataclass
from enum import Enum

from big_pig_farm.data.config import ECONOMY, TIER_UPGRADES, TierUpgrade
from big_pig_farm.economy.currency import add_money, spend_money
from big_pig_farm.entities.biomes import BIOMES, BiomeType
from big_pig_farm.entities.facilities import Facility, FacilityType
from big_pig_farm.game.state import GameState


class ShopCategory(str, Enum):
    """Shop item categories."""
    FACILITIES = "facilities"
    UPGRADES = "upgrades"
    FOOD = "food"
    DECORATIONS = "decorations"
    ADOPTION = "adoption"


@dataclass
class ShopItem:
    """An item available for purchase in the shop."""
    id: str
    name: str
    description: str
    cost: int
    category: ShopCategory
    facility_type: FacilityType | None = None
    unlocked: bool = True
    required_tier: int = 1


# Define all shop items
SHOP_ITEMS: list[ShopItem] = [
    # Basic facilities (Tier 1)
    ShopItem(
        id="food_bowl",
        name="Food Bowl",
        description="Feeds pigs to reduce hunger. Capacity: 100 units. Size: 2x1. Refill cost: 5 Squeaks.",
        cost=ECONOMY.FOOD_BOWL_COST,
        category=ShopCategory.FACILITIES,
        facility_type=FacilityType.FOOD_BOWL,
        required_tier=1,
    ),
    ShopItem(
        id="water_bottle",
        name="Water Bottle",
        description="Hydrates pigs to reduce thirst. Capacity: 100 units. Size: 1x2. Refill cost: 2 Squeaks.",
        cost=ECONOMY.WATER_BOTTLE_COST,
        category=ShopCategory.FACILITIES,
        facility_type=FacilityType.WATER_BOTTLE,
        required_tier=1,
    ),
    ShopItem(
        id="hay_rack",
        name="Hay Rack",
        description="Alternative food source — pigs prefer it over food bowls. +5% health bonus while eating. Capacity: 100 units. Size: 2x1.",
        cost=ECONOMY.HAY_RACK_COST,
        category=ShopCategory.FACILITIES,
        facility_type=FacilityType.HAY_RACK,
        required_tier=2,
    ),
    ShopItem(
        id="hideout",
        name="Hideout",
        description="Pigs sleep here to restore energy. +10% happiness bonus while resting. Fits 2 pigs at once. Size: 3x2.",
        cost=ECONOMY.HIDEOUT_COST,
        category=ShopCategory.FACILITIES,
        facility_type=FacilityType.HIDEOUT,
        required_tier=1,
    ),
    # Tier 2 facilities
    ShopItem(
        id="exercise_wheel",
        name="Exercise Wheel",
        description="Pigs play here to reduce boredom. +5% health bonus while playing. Size: 2x2.",
        cost=ECONOMY.EXERCISE_WHEEL_COST,
        category=ShopCategory.FACILITIES,
        facility_type=FacilityType.EXERCISE_WHEEL,
        required_tier=2,
    ),
    ShopItem(
        id="tunnel",
        name="Tunnel System",
        description="Pigs play here to reduce boredom. +15% happiness bonus while playing. Size: 3x1.",
        cost=ECONOMY.TUNNEL_COST,
        category=ShopCategory.FACILITIES,
        facility_type=FacilityType.TUNNEL,
        required_tier=2,
    ),
    # Tier 3 facilities
    ShopItem(
        id="play_area",
        name="Play Area",
        description="Pigs play and socialize here — reduces boredom and fulfills social needs. +20% social bonus. Size: 3x2.",
        cost=ECONOMY.PLAY_AREA_COST,
        category=ShopCategory.FACILITIES,
        facility_type=FacilityType.PLAY_AREA,
        required_tier=3,
    ),
    # Tier 4 facilities
    ShopItem(
        id="breeding_den",
        name="Breeding Den",
        description="+15% breeding success rate. Required for pigs to mate. Size: 2x2.",
        cost=ECONOMY.BREEDING_DEN_COST,
        category=ShopCategory.FACILITIES,
        facility_type=FacilityType.BREEDING_DEN,
        required_tier=4,
    ),
    ShopItem(
        id="nursery",
        name="Nursery",
        description="Newborn pigs grow 20% faster near a nursery. Fits 4 pigs. Size: 3x2.",
        cost=ECONOMY.NURSERY_COST,
        category=ShopCategory.FACILITIES,
        facility_type=FacilityType.NURSERY,
        required_tier=4,
    ),
    ShopItem(
        id="veggie_garden",
        name="Veggie Garden",
        description="Produces 10 food units per day, auto-refilling nearby food bowls. Size: 2x2.",
        cost=ECONOMY.VEGGIE_GARDEN_COST,
        category=ShopCategory.FACILITIES,
        facility_type=FacilityType.VEGGIE_GARDEN,
        required_tier=4,
    ),
    ShopItem(
        id="grooming_station",
        name="Grooming Station",
        description="Pigs that use this sell for +15% more at market. Size: 2x1.",
        cost=ECONOMY.GROOMING_STATION_COST,
        category=ShopCategory.FACILITIES,
        facility_type=FacilityType.GROOMING_STATION,
        required_tier=3,
    ),
    ShopItem(
        id="genetics_lab",
        name="Genetics Lab",
        description="Reveals carrier alleles on pig detail screen and boosts mutation rate from 2% to 3% per locus. Size: 3x2.",
        cost=ECONOMY.GENETICS_LAB_COST,
        category=ShopCategory.FACILITIES,
        facility_type=FacilityType.GENETICS_LAB,
        required_tier=3,
    ),
    # Food items
    ShopItem(
        id="food_refill",
        name="Food Refill",
        description="Refills all food bowls and hay racks to max capacity instantly.",
        cost=10,
        category=ShopCategory.FOOD,
        required_tier=1,
    ),
    ShopItem(
        id="water_refill",
        name="Water Refill",
        description="Refills all water bottles to max capacity instantly.",
        cost=5,
        category=ShopCategory.FOOD,
        required_tier=1,
    ),
    ShopItem(
        id="premium_food",
        name="Premium Food Pack",
        description="Instantly boosts happiness by +20 for all pigs on the farm.",
        cost=25,
        category=ShopCategory.FOOD,
        required_tier=2,
    ),
]


def get_shop_items(category: ShopCategory | None = None, farm_tier: int = 1) -> list[ShopItem]:
    """Get shop items, optionally filtered by category."""
    items = SHOP_ITEMS

    if category:
        items = [i for i in items if i.category == category]

    # Mark items as unlocked based on farm tier
    result = []
    for item in items:
        item_copy = ShopItem(
            id=item.id,
            name=item.name,
            description=item.description,
            cost=item.cost,
            category=item.category,
            facility_type=item.facility_type,
            unlocked=item.required_tier <= farm_tier,
            required_tier=item.required_tier,
        )
        result.append(item_copy)

    return result


def purchase_item(state: GameState, item: ShopItem, position: tuple[int, int] | None = None) -> bool:
    """Attempt to purchase a shop item. Returns True if successful."""
    if not item.unlocked:
        return False

    if state.money < item.cost:
        return False

    # Handle facility placement
    if item.facility_type and position:
        facility = Facility.create(item.facility_type, position[0], position[1])
        if not state.add_facility(facility):
            return False  # Couldn't place facility

    # Deduct cost
    if not spend_money(state, item.cost, f"Purchased {item.name}"):
        return False

    # Handle special items
    if item.id == "food_refill":
        _refill_all_facilities(state, FacilityType.FOOD_BOWL)
        _refill_all_facilities(state, FacilityType.HAY_RACK)
    elif item.id == "water_refill":
        _refill_all_facilities(state, FacilityType.WATER_BOTTLE)
    elif item.id == "premium_food":
        _boost_all_happiness(state, 20.0)

    return True


def _refill_all_facilities(state: GameState, facility_type: FacilityType) -> None:
    """Refill all facilities of a given type."""
    for facility in state.get_facilities_by_type(facility_type):
        facility.refill()


def _boost_all_happiness(state: GameState, amount: float) -> None:
    """Boost happiness for all pigs on the farm."""
    for pig in state.get_pigs_list():
        pig.needs.happiness = min(100.0, pig.needs.happiness + amount)
        pig.needs.clamp_all()


def get_facility_cost(facility_type: FacilityType) -> int:
    """Get the purchase cost of a facility type."""
    for item in SHOP_ITEMS:
        if item.facility_type == facility_type:
            return item.cost
    return 0


def sell_facility(state: GameState, facility) -> int:
    """Remove a facility and refund its cost. Returns refund amount."""
    cost = get_facility_cost(facility.facility_type)
    state.remove_facility(facility.id)
    add_money(state, cost, f"Removed {facility.facility_type.display_name}")
    return cost


def get_current_tier_upgrade(tier: int) -> TierUpgrade | None:
    """Get the TierUpgrade definition for the given tier, or None."""
    for upgrade in TIER_UPGRADES:
        if upgrade.tier == tier:
            return upgrade
    return None


def get_next_tier_upgrade(state: GameState) -> TierUpgrade | None:
    """Get the next tier upgrade, or None if at max tier."""
    for upgrade in TIER_UPGRADES:
        if upgrade.tier == state.farm_tier + 1:
            return upgrade
    return None


def check_tier_requirements(state: GameState, upgrade: TierUpgrade) -> dict[str, bool]:
    """Check which requirements are met for a tier upgrade."""
    completed = state.contract_board.completed_contracts
    return {
        "pigs_born": state.total_pigs_born >= upgrade.required_pigs_born,
        "pigdex": state.pigdex.discovered_count >= upgrade.required_pigdex,
        "contracts": completed >= upgrade.required_contracts,
        "money": state.money >= upgrade.cost,
    }


def purchase_tier_upgrade(state: GameState) -> bool:
    """Purchase the next tier upgrade. Returns True if successful."""
    upgrade = get_next_tier_upgrade(state)
    if upgrade is None:
        return False

    reqs = check_tier_requirements(state, upgrade)
    if not all(reqs.values()):
        return False

    if not spend_money(state, upgrade.cost):
        return False

    state.farm_tier = upgrade.tier
    state.log_event(f"Farm upgraded to Tier {upgrade.tier}: {upgrade.name}!", "purchase")
    return True


def get_farm_upgrade_info(state: GameState) -> dict | None:
    """Get info about the next room addition, or None if at max or capped."""
    # Check room cap for current tier
    current = get_current_tier_upgrade(state.farm_tier)
    if current is None:
        return None
    if len(state.farm.areas) >= current.max_rooms:
        return None

    next_tier = state.farm.next_room_tier
    if next_tier is None:
        return None

    return {
        "name": next_tier.name,
        "cost": next_tier.cost,
        "width": next_tier.room_width,
        "height": next_tier.room_height,
        "capacity": next_tier.capacity_add,
        "tier": next_tier.tier,
    }


def get_room_total_cost(state: GameState, biome: BiomeType) -> int:
    """Get the total cost for adding a room with the given biome."""
    next_tier = state.farm.next_room_tier
    if next_tier is None:
        return 0
    return next_tier.cost + BIOMES[biome].cost


def purchase_new_room(state: GameState, biome: BiomeType) -> bool:
    """Add a new room with the given biome. Returns True if successful."""
    total_cost = get_room_total_cost(state, biome)
    if total_cost <= 0:
        return False
    if state.money < total_cost:
        return False

    result = state.farm.add_room(biome)
    if result is None:
        return False

    new_area, tunnels, offset_x, offset_y = result

    # Shift entities if grid expanded
    if offset_x or offset_y:
        for facility in state.get_facilities_list():
            facility.position_x += offset_x
            facility.position_y += offset_y

        for pig in state.get_pigs_list():
            pig.position.x += offset_x
            pig.position.y += offset_y
            pig.path = []
            pig.target_position = None

    state.spend_money(total_cost)
    biome_name = BIOMES[biome].display_name
    state.log_event(f"Added {new_area.name} ({biome_name} biome)!", "purchase")

    return True


def purchase_farm_upgrade(state: GameState) -> bool:
    """Legacy farm upgrade — now adds a MEADOW room."""
    return purchase_new_room(state, BiomeType.MEADOW)
