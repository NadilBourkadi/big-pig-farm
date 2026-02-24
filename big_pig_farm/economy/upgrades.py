"""Permanent upgrade (perk) definitions for the shop."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UpgradeDefinition:
    """A permanent one-time upgrade purchasable from the Perks tab."""

    id: str
    name: str
    description: str
    cost: int
    required_tier: int
    category: str  # Grouping label for display: Automation, Breeding, etc.
    implemented: bool = False  # Only show in shop when True


# All upgrades keyed by ID for O(1) lookup
UPGRADES: dict[str, UpgradeDefinition] = {}


def _register(*defs: UpgradeDefinition) -> None:
    for definition in defs:
        UPGRADES[definition.id] = definition


# --- Automation ---
_register(
    UpgradeDefinition(
        id="bulk_feeders",
        name="Bulk Feeders",
        description="All food/water facility capacity doubled.",
        cost=150,
        required_tier=2,
        category="Automation",
        implemented=True,
    ),
    UpgradeDefinition(
        id="drip_system",
        name="Drip System",
        description="Food/water facilities passively regen 2 units per game-hour.",
        cost=500,
        required_tier=3,
        category="Automation",
        implemented=True,
    ),
    UpgradeDefinition(
        id="auto_feeders",
        name="Auto-Feeders",
        description="Facilities auto-refill to full when below 25% capacity.",
        cost=2000,
        required_tier=4,
        category="Automation",
        implemented=True,
    ),
)

# --- Breeding & Genetics ---
_register(
    UpgradeDefinition(
        id="fertility_herbs",
        name="Fertility Herbs",
        description="+5% base breeding chance.",
        cost=200,
        required_tier=2,
        category="Breeding",
    ),
    UpgradeDefinition(
        id="breeding_insight",
        name="Breeding Insight",
        description="Pig detail shows offspring phenotype probabilities for selected pairs.",
        cost=600,
        required_tier=3,
        category="Breeding",
    ),
    UpgradeDefinition(
        id="litter_boost",
        name="Litter Boost",
        description="Max litter size +1.",
        cost=3000,
        required_tier=4,
        category="Breeding",
    ),
    UpgradeDefinition(
        id="genetic_accelerator",
        name="Genetic Accelerator",
        description="Mutation rate doubled (stacks with Genetics Lab).",
        cost=8000,
        required_tier=5,
        category="Breeding",
    ),
)

# --- Comfort & Needs ---
_register(
    UpgradeDefinition(
        id="premium_bedding",
        name="Premium Bedding",
        description="Energy recovery while sleeping +25%.",
        cost=150,
        required_tier=2,
        category="Comfort",
    ),
    UpgradeDefinition(
        id="enrichment_program",
        name="Enrichment Program",
        description="Boredom grows 20% slower.",
        cost=400,
        required_tier=3,
        category="Comfort",
    ),
    UpgradeDefinition(
        id="climate_control",
        name="Climate Control",
        description="All biomes grant +0.3 happiness/hr.",
        cost=600,
        required_tier=3,
        category="Comfort",
    ),
    UpgradeDefinition(
        id="pig_spa",
        name="Pig Spa Package",
        description="Passive health recovery doubled.",
        cost=1500,
        required_tier=4,
        category="Comfort",
    ),
)

# --- Economy & Sales ---
_register(
    UpgradeDefinition(
        id="market_connections",
        name="Market Connections",
        description="All pig sale values +10%.",
        cost=250,
        required_tier=2,
        category="Economy",
    ),
    UpgradeDefinition(
        id="premium_branding",
        name="Premium Branding",
        description="Rare+ pigs sell for additional +20%.",
        cost=800,
        required_tier=3,
        category="Economy",
    ),
    UpgradeDefinition(
        id="trade_network",
        name="Trade Network",
        description="Contract reward payouts +25%.",
        cost=2500,
        required_tier=4,
        category="Economy",
    ),
    UpgradeDefinition(
        id="influencer_pig",
        name="Influencer Pig",
        description="Legendary pigs sell for +50%.",
        cost=10000,
        required_tier=5,
        category="Economy",
    ),
)

# --- Movement ---
_register(
    UpgradeDefinition(
        id="paved_paths",
        name="Paved Paths",
        description="Pig movement speed +20%.",
        cost=200,
        required_tier=2,
        category="Movement",
    ),
    UpgradeDefinition(
        id="express_lanes",
        name="Express Lanes",
        description="Pig movement speed +50% (replaces Paved Paths).",
        cost=1200,
        required_tier=4,
        category="Movement",
    ),
)

# --- Quality of Life ---
_register(
    UpgradeDefinition(
        id="farm_bell",
        name="Farm Bell",
        description="Notification when any pig's hunger/thirst drops below critical.",
        cost=100,
        required_tier=2,
        category="Quality of Life",
    ),
    UpgradeDefinition(
        id="adoption_discount",
        name="Adoption Discount",
        description="Adoption prices permanently -15%.",
        cost=150,
        required_tier=2,
        category="Quality of Life",
    ),
    UpgradeDefinition(
        id="speed_breeding",
        name="Speed Breeding License",
        description="Pregnancy duration -25%.",
        cost=500,
        required_tier=3,
        category="Quality of Life",
    ),
    UpgradeDefinition(
        id="contract_negotiator",
        name="Contract Negotiator",
        description="+1 max active contract slot.",
        cost=400,
        required_tier=3,
        category="Quality of Life",
    ),
    UpgradeDefinition(
        id="lucky_clover",
        name="Lucky Clover",
        description="Pigdex discoveries award bonus 50-200 Squeaks (10% chance).",
        cost=2000,
        required_tier=4,
        category="Quality of Life",
    ),
    UpgradeDefinition(
        id="vip_contracts",
        name="VIP Contract Access",
        description="Unlocks LEGENDARY contract difficulty (all 4 axes + roan, huge reward).",
        cost=6000,
        required_tier=5,
        category="Quality of Life",
    ),
    UpgradeDefinition(
        id="talent_scout",
        name="Talent Scout",
        description="Enables the Pig Talents system.",
        cost=400,
        required_tier=3,
        category="Quality of Life",
    ),
)
