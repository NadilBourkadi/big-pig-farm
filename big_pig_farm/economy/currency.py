"""Money management for the game."""

from big_pig_farm.game.state import GameState


def add_money(state: GameState, amount: int, reason: str = "") -> None:
    """Add money to the player's balance and log the transaction."""
    state.add_money(amount)
    if reason:
        state.log_event(f"Earned {amount} Squeaks: {reason}", event_type="income")


def spend_money(state: GameState, amount: int, reason: str = "") -> bool:
    """Spend money if available. Returns True if successful."""
    if state.spend_money(amount):
        if reason:
            state.log_event(f"Spent {amount} Squeaks: {reason}", event_type="purchase")
        return True
    return False


def can_afford(state: GameState, amount: int) -> bool:
    """Check if player can afford an amount."""
    return state.money >= amount


def format_money(amount: int) -> str:
    """Format money amount for display."""
    if amount >= 1000000:
        return f"{amount / 1000000:.1f}M"
    elif amount >= 1000:
        return f"{amount / 1000:.1f}K"
    return str(amount)
