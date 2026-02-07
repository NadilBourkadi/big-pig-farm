"""Bloodline types for adoption center pigs with hidden carrier alleles."""

import random
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from big_pig_farm.entities.genetics import Genotype


class BloodlineType(str, Enum):
    """Types of bloodlines available for adoption."""
    SPOTTED = "spotted"
    CHOCOLATE = "chocolate"
    GOLDEN = "golden"
    SILVER = "silver"
    ROAN = "roan"
    EXOTIC_SPOT_SILVER = "exotic_spot_silver"
    EXOTIC_ROAN_SILVER = "exotic_roan_silver"


class Bloodline(BaseModel):
    """A bloodline definition with carrier alleles and tier gating."""
    bloodline_type: BloodlineType
    display_name: str
    description: str
    required_tier: int
    cost_multiplier: float
    locus_overrides: dict[str, tuple[str, str]]

    def apply_to_genotype(self, genotype: Genotype) -> Genotype:
        """Apply bloodline carrier alleles on top of a genotype."""
        data = genotype.model_dump()
        for locus_name, alleles in self.locus_overrides.items():
            data[locus_name] = alleles
        return Genotype(**data)


BLOODLINES: dict[BloodlineType, Bloodline] = {
    BloodlineType.SPOTTED: Bloodline(
        bloodline_type=BloodlineType.SPOTTED,
        display_name="Spotted Bloodline",
        description="May produce offspring with unusual patterns",
        required_tier=1,
        cost_multiplier=1.5,
        locus_overrides={"s_locus": ("S", "s")},
    ),
    BloodlineType.CHOCOLATE: Bloodline(
        bloodline_type=BloodlineType.CHOCOLATE,
        display_name="Chocolate Bloodline",
        description="May produce offspring with rich chocolate coloring",
        required_tier=1,
        cost_multiplier=1.3,
        locus_overrides={"b_locus": ("B", "b")},
    ),
    BloodlineType.GOLDEN: Bloodline(
        bloodline_type=BloodlineType.GOLDEN,
        display_name="Golden Bloodline",
        description="May produce offspring with golden or cream coloring",
        required_tier=2,
        cost_multiplier=1.8,
        locus_overrides={"e_locus": ("E", "e")},
    ),
    BloodlineType.SILVER: Bloodline(
        bloodline_type=BloodlineType.SILVER,
        display_name="Silver Bloodline",
        description="May produce offspring with unusual color intensity",
        required_tier=2,
        cost_multiplier=2.5,
        locus_overrides={"c_locus": ("C", "ch")},
    ),
    BloodlineType.ROAN: Bloodline(
        bloodline_type=BloodlineType.ROAN,
        display_name="Roan Bloodline",
        description="Carries the roan gene — white hairs mixed into coat",
        required_tier=3,
        cost_multiplier=3.0,
        locus_overrides={"r_locus": ("R", "r")},
    ),
    BloodlineType.EXOTIC_SPOT_SILVER: Bloodline(
        bloodline_type=BloodlineType.EXOTIC_SPOT_SILVER,
        display_name="Exotic Bloodline (Spotted+Silver)",
        description="Carries both spotting and intensity genes — rare combos possible",
        required_tier=4,
        cost_multiplier=4.0,
        locus_overrides={"s_locus": ("S", "s"), "c_locus": ("C", "ch")},
    ),
    BloodlineType.EXOTIC_ROAN_SILVER: Bloodline(
        bloodline_type=BloodlineType.EXOTIC_ROAN_SILVER,
        display_name="Exotic Bloodline (Roan+Silver)",
        description="Carries both roan and intensity genes — legendary combos possible",
        required_tier=4,
        cost_multiplier=5.0,
        locus_overrides={"r_locus": ("R", "r"), "c_locus": ("C", "ch")},
    ),
}


def get_available_bloodlines(farm_tier: int) -> list[Bloodline]:
    """Get bloodlines available at the given farm tier."""
    return [b for b in BLOODLINES.values() if b.required_tier <= farm_tier]


def generate_bloodline_pig_genotype(bloodline: Bloodline) -> Genotype:
    """Generate a genotype with bloodline carrier alleles applied."""
    base = Genotype.random_common()
    return bloodline.apply_to_genotype(base)


def pick_random_bloodline(farm_tier: int) -> Optional[Bloodline]:
    """Pick a random available bloodline for the given tier."""
    available = get_available_bloodlines(farm_tier)
    if not available:
        return None
    return random.choice(available)
