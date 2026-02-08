"""Shared UI formatting utilities."""


def format_needs_bar(value: float, width: int = 10) -> str:
    """Create a consistent needs bar visualization.

    Format: ██████░░░░  60%
    Used in sidebar, pig detail, and pig list.
    """
    filled = int((value / 100) * width)
    empty = width - filled
    pct = f"{int(value):3d}%"
    return "\u2588" * filled + "\u2591" * empty + " " + pct
