"""Random events and notifications for the game."""

import random
from enum import Enum
from typing import Optional

from big_pig_farm.game.state import GameState


class EventType(str, Enum):
    """Types of random events."""
    VISITOR = "visitor"
    ILLNESS = "illness"
    ESCAPE = "escape"
    COMPETITION = "competition"
    WEATHER = "weather"


class RandomEvent:
    """A random event that can occur in the game."""

    def __init__(
        self,
        event_type: EventType,
        message: str,
        effect_func: Optional[callable] = None,
    ):
        self.event_type = event_type
        self.message = message
        self.effect_func = effect_func

    def apply(self, state: GameState) -> str:
        """Apply the event effects and return a message."""
        if self.effect_func:
            return self.effect_func(state)
        return self.message


def _visitor_event(state: GameState) -> str:
    """A visitor comes to admire the guinea pigs."""
    # Small passive income
    tip = random.randint(5, 15)
    state.add_money(tip)
    return f"A visitor admired your guinea pigs and left a {tip} Squeak tip!"


def _good_weather_event(state: GameState) -> str:
    """Good weather boosts happiness."""
    for pig in state.get_pigs_list():
        pig.needs.happiness = min(100, pig.needs.happiness + 10)
    return "Beautiful weather today! All guinea pigs feel happier."


def _illness_event(state: GameState) -> str:
    """A guinea pig gets slightly ill."""
    pigs = state.get_pigs_list()
    if not pigs:
        return ""

    sick_pig = random.choice(pigs)
    sick_pig.needs.health -= 10
    sick_pig.needs.happiness -= 15
    return f"{sick_pig.name} is feeling under the weather."


# Pool of possible random events
RANDOM_EVENTS = [
    RandomEvent(EventType.VISITOR, "", _visitor_event),
    RandomEvent(EventType.WEATHER, "", _good_weather_event),
    RandomEvent(EventType.ILLNESS, "", _illness_event),
]


def check_random_event(state: GameState, chance: float = 0.01) -> Optional[str]:
    """Check if a random event should occur.

    Args:
        state: Current game state
        chance: Probability of event occurring (0-1)

    Returns:
        Event message if event occurred, None otherwise
    """
    if random.random() > chance:
        return None

    # Weight events (visitors more common than illness)
    weights = [0.5, 0.35, 0.15]  # visitor, weather, illness

    event = random.choices(RANDOM_EVENTS, weights=weights, k=1)[0]
    message = event.apply(state)

    if message:
        state.log_event(message, event_type=event.event_type.value)

    return message
