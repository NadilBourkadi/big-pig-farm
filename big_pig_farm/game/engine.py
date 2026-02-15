"""Game engine - tick management and simulation loop."""

import asyncio
import logging
from datetime import datetime
from typing import Callable, Optional

from big_pig_farm.data.config import SIMULATION, TIME, GameSpeed
from big_pig_farm.game.state import GameState

logger = logging.getLogger(__name__)


class GameEngine:
    """Main game engine that drives the simulation."""

    def __init__(self, state: GameState):
        self.state = state
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._tick_callbacks: list[Callable[[float], None]] = []
        self._last_tick_time: float = 0.0

    def register_tick_callback(self, callback: Callable[[float], None]) -> None:
        """Register a callback to be called each tick with delta time."""
        self._tick_callbacks.append(callback)

    def unregister_tick_callback(self, callback: Callable[[float], None]) -> None:
        """Remove a tick callback."""
        if callback in self._tick_callbacks:
            self._tick_callbacks.remove(callback)

    async def start(self) -> None:
        """Start the game loop."""
        if self._running:
            return

        self._running = True
        self._last_tick_time = asyncio.get_event_loop().time()
        self._task = asyncio.create_task(self._game_loop())

    async def stop(self) -> None:
        """Stop the game loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def pause(self) -> None:
        """Pause the simulation."""
        self.state.is_paused = True

    def resume(self) -> None:
        """Resume the simulation."""
        self.state.is_paused = False

    def toggle_pause(self) -> bool:
        """Toggle pause state. Returns new pause state."""
        self.state.is_paused = not self.state.is_paused
        return self.state.is_paused

    def set_speed(self, speed: GameSpeed) -> None:
        """Set the game speed."""
        self.state.speed = speed

    def cycle_speed(self, debug: bool = False) -> GameSpeed:
        """Cycle through speed settings. Returns new speed."""
        speeds = [GameSpeed.NORMAL, GameSpeed.FAST, GameSpeed.FASTER, GameSpeed.FASTEST]
        if debug:
            speeds.extend([GameSpeed.DEBUG, GameSpeed.DEBUG_FAST])
        current_idx = speeds.index(self.state.speed) if self.state.speed in speeds else 0
        new_idx = (current_idx + 1) % len(speeds)
        self.state.speed = speeds[new_idx]
        return self.state.speed

    async def _game_loop(self) -> None:
        """Main game loop."""
        tick_interval = 1.0 / SIMULATION.TICKS_PER_SECOND
        max_delta = 0.5  # Cap delta to handle laptop sleep/wake gracefully

        while self._running:
            current_time = asyncio.get_event_loop().time()
            delta_time = current_time - self._last_tick_time
            self._last_tick_time = current_time

            # Clamp delta to prevent huge time jumps after sleep/wake
            delta_time = min(delta_time, max_delta)

            if not self.state.is_paused and self.state.speed != GameSpeed.PAUSED:
                # Scale delta time by game speed
                game_delta = delta_time * self.state.speed.value
                await self._tick(game_delta)

            # Update last update timestamp
            self.state.game_time.last_update = datetime.now()

            # Wait for next tick
            await asyncio.sleep(tick_interval)

    async def _tick(self, delta_seconds: float) -> None:
        """Process a single game tick."""
        # Convert real seconds to game minutes
        # At 1x speed: 1 real second = 1 game minute
        game_minutes = delta_seconds / TIME.REAL_SECONDS_PER_GAME_MINUTE

        # Advance game time
        self.state.game_time.advance(game_minutes)

        # Call all registered tick callbacks
        for callback in self._tick_callbacks:
            try:
                callback(delta_seconds)
            except Exception:
                # Log but don't crash the game loop
                logger.exception("Tick callback error")

