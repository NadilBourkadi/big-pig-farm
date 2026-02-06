"""Game engine - tick management and simulation loop."""

import asyncio
from datetime import datetime
from typing import Callable, Optional

from big_pig_farm.data.config import SIMULATION, TIME, GameSpeed
from big_pig_farm.game.state import GameState


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

    def cycle_speed(self) -> GameSpeed:
        """Cycle through speed settings. Returns new speed."""
        speeds = [GameSpeed.NORMAL, GameSpeed.FAST, GameSpeed.FASTER, GameSpeed.FASTEST]
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
            except Exception as e:
                # Log but don't crash the game loop
                print(f"Tick callback error: {e}")

    def calculate_offline_progress(self) -> dict:
        """Calculate what happened while the game was closed.

        Returns a summary dict of events that occurred.
        """
        now = datetime.now()
        last_update = self.state.game_time.last_update
        elapsed_seconds = (now - last_update).total_seconds()

        # Cap at maximum offline time
        max_offline_seconds = TIME.MAX_OFFLINE_HOURS * 3600
        elapsed_seconds = min(elapsed_seconds, max_offline_seconds)

        if elapsed_seconds < 60:  # Less than a minute, no offline progress
            return {"skipped": True, "reason": "Too short"}

        # Convert to game time
        game_hours = elapsed_seconds / 3600  # Real hours

        summary = {
            "real_hours": elapsed_seconds / 3600,
            "game_days": game_hours,  # At 1x, 1 real hour = 60 game minutes = 1 game hour
            "events": [],
            "births": 0,
            "deaths": 0,
            "income": 0,
        }

        # Simplified offline simulation
        # We simulate in hourly chunks
        hours_to_simulate = int(game_hours)

        for _ in range(hours_to_simulate):
            self._simulate_offline_hour(summary)

        # Update game time
        self.state.game_time.advance(game_hours * 60)

        return summary

    def _simulate_offline_hour(self, summary: dict) -> None:
        """Simulate one hour of offline progression."""
        from big_pig_farm.simulation.needs import update_all_needs
        from big_pig_farm.simulation.breeding import check_breeding_opportunities

        # Update needs for all pigs (simplified)
        for pig in self.state.get_pigs_list():
            update_all_needs(pig, 60.0, self.state)  # 60 game minutes

        # Check for breeding
        births = check_breeding_opportunities(self.state)
        summary["births"] += births

        # Passive income (if any facilities generate it)
        # This would be expanded based on facilities
