"""Shared UI formatting utilities."""

from big_pig_farm.entities.facilities import FacilityInfo, FacilityType, FACILITY_INFO
from big_pig_farm.entities.guinea_pig import GuineaPig


def format_needs_bar(value: float, width: int = 10) -> str:
    """Create a consistent needs bar visualization.

    Format: ██████░░░░  60%
    Used in sidebar, pig detail, and pig list.
    """
    filled = int((value / 100) * width)
    empty = width - filled
    pct = f"{int(value):3d}%"
    return "\u2588" * filled + "\u2591" * empty + " " + pct


def format_breeding_status(pig: GuineaPig, verbose: bool = False) -> str:
    """Format breeding status consistently.

    Short form (verbose=False): "Sell@Adult", "LOCKED", "Pregnant", "Baby", "Ready", etc.
    Verbose form (verbose=True): uses breeding_block_reason for full detail.
    """
    if pig.is_baby and pig.marked_for_sale:
        return "Sell@Adult" if not verbose else "Marked for auto-sell at adulthood"
    if pig.can_breed:
        return "Ready"

    reason = pig.breeding_block_reason
    if verbose:
        return reason or "Not ready"

    # Derive short labels from the reason
    if reason is not None:
        if reason.startswith("Breeding locked"):
            return "LOCKED"
        if reason.startswith("Too young"):
            return "Baby"
        if reason.startswith("Too old"):
            return "Senior"
        if reason.startswith("Unhappy"):
            return "Not ready"
        if reason.startswith("Pregnant"):
            return "Pregnant"
        if reason.startswith("Recovering"):
            return "Recovering"
    return "Not ready"


def format_facility_bonuses(facility_type: FacilityType) -> str:
    """Format facility bonuses as a short summary string.

    Returns empty string if no bonuses.
    """
    info = FACILITY_INFO[facility_type]
    parts = []
    if info.health_bonus:
        parts.append(f"+{int(info.health_bonus * 100)}% health")
    if info.happiness_bonus:
        parts.append(f"+{int(info.happiness_bonus * 100)}% happiness")
    if info.social_bonus:
        parts.append(f"+{int(info.social_bonus * 100)}% social")
    if info.breeding_bonus:
        parts.append(f"+{int(info.breeding_bonus * 100)}% breeding")
    if info.growth_bonus:
        parts.append(f"+{int(info.growth_bonus * 100)}% growth")
    if info.sale_bonus:
        parts.append(f"+{int(info.sale_bonus * 100)}% sale value")
    if info.food_production:
        parts.append(f"produces {info.food_production} food")
    return ", ".join(parts)
