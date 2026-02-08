"""Shared UI formatting utilities."""

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

    Short form (verbose=False): "Sell@Adult", "LOCKED", "Pregnant", "Baby", "Ready", "Not ready"
    Verbose form (verbose=True): adds details like pregnancy countdown.
    """
    if pig.is_baby and pig.marked_for_sale:
        return "Sell@Adult" if not verbose else "Marked for auto-sell at adulthood"
    if pig.breeding_locked:
        return "LOCKED" if not verbose else "Breeding locked"
    if pig.is_pregnant:
        days_left = max(0, 3 - pig.pregnancy_days)
        if verbose:
            return f"Pregnant ({days_left:.1f}d left)"
        return "Pregnant"
    if not pig.is_adult:
        return "Baby" if not verbose else "Too young (must be 3+ days)"
    if pig.can_breed:
        return "Ready"
    return "Not ready" if not verbose else "Not ready (needs higher happiness)"
