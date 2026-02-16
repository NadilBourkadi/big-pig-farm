"""Debug logger that writes periodic game state snapshots to a file."""

import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from big_pig_farm.data.config import SPEED_DISPLAY
from big_pig_farm.entities.guinea_pig import Gender
from big_pig_farm.game.state import GameState
from big_pig_farm.simulation.behavior import BehaviorController


class DebugLogger:
    """Appends compact state snapshots to a rolling log file."""

    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
    SNAPSHOT_INTERVAL = 50  # ticks between snapshots (~5 seconds)

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(exist_ok=True)
        self._tick_counter = 0
        self._total_ticks = 0
        self._last_logs: dict[UUID, int] = {}  # pig_id -> log length at last snapshot
        self._last_event_count: int = 0
        # Performance tracking
        self._tick_times: list[float] = []  # ms per tick in current window
        self._window_start: float = time.monotonic()
        # Phase timing accumulator across the snapshot window
        self._phase_totals: dict[str, float] = {}
        # Start fresh each session
        self.path.write_text(
            f"=== Debug session started {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n"
        )

    def tick(
        self,
        state: GameState,
        controller: BehaviorController,
        tick_ms: float = 0.0,
        phase_times: Optional[dict[str, float]] = None,
    ) -> None:
        """Called every simulation tick. Writes a snapshot every SNAPSHOT_INTERVAL ticks."""
        self._total_ticks += 1
        self._tick_counter += 1
        self._tick_times.append(tick_ms)
        if phase_times:
            for phase, ms in phase_times.items():
                self._phase_totals[phase] = self._phase_totals.get(phase, 0.0) + ms
        if self._tick_counter < self.SNAPSHOT_INTERVAL:
            return
        self._tick_counter = 0
        self._write_snapshot(state, controller)

    def _write_snapshot(self, state: GameState, controller: BehaviorController) -> None:
        # Skip snapshots when no pigs exist (e.g. during save/load, speed
        # change, or before initial pigs are created).  Reset perf counters
        # so the next valid snapshot starts fresh rather than accumulating
        # data from empty windows.
        if not state.get_pigs_list():
            state.farm.reset_perf_counters()
            controller.facility_manager.reset_perf_counters()
            self._tick_times.clear()
            self._window_start = time.monotonic()
            self._phase_totals.clear()
            return

        now = datetime.now().strftime("%H:%M:%S")
        lines = [f"--- TICK {self._total_ticks} | {now} | speed={SPEED_DISPLAY[state.speed]} ---"]

        # Performance stats for the window
        if self._tick_times:
            window_elapsed = time.monotonic() - self._window_start
            n = len(self._tick_times)
            avg_ms = sum(self._tick_times) / n
            max_ms = max(self._tick_times)
            actual_tps = n / window_elapsed if window_elapsed > 0 else 0
            lines.append(
                f"  PERF: {actual_tps:.1f} tps | tick avg={avg_ms:.2f}ms max={max_ms:.2f}ms"
                f" | {n} ticks in {window_elapsed:.1f}s"
            )

            # Per-phase timing breakdown
            if self._phase_totals and n > 0:
                parts = []
                for phase in ("needs", "behavior", "collision", "breeding"):
                    total_ms = self._phase_totals.get(phase, 0.0)
                    parts.append(f"{phase}={total_ms / n:.2f}ms")
                lines.append(f"  PHASES: {' | '.join(parts)}")
                self._phase_totals.clear()

            self._tick_times.clear()
            self._window_start = time.monotonic()

        # A* pathfinding stats
        farm = state.farm
        calls = farm._pathfind_calls
        nodes = farm._pathfind_nodes
        avg_nodes = nodes / calls if calls > 0 else 0
        fm = controller.facility_manager
        cache_total = fm.cache_hits + fm.cache_misses
        hit_pct = (fm.cache_hits / cache_total * 100) if cache_total > 0 else 0
        lines.append(
            f"  A*: {calls} calls | {nodes} nodes (avg {avg_nodes:.0f}/call)"
            f" | cache {fm.cache_hits}/{cache_total} ({hit_pct:.0f}% hit)"
        )
        farm.reset_perf_counters()
        fm.reset_perf_counters()

        # Path length stats (current snapshot of all pig paths)
        pigs = state.get_pigs_list()
        path_lengths = [len(p.path) for p in pigs if p.path]
        if path_lengths:
            avg_path = sum(path_lengths) / len(path_lengths)
            max_path = max(path_lengths)
            lines.append(
                f"  PATHS: {len(path_lengths)} active | avg={avg_path:.0f} max={max_path}"
            )

        # Behavior state distribution
        state_counts: Counter[str] = Counter()
        for pig in pigs:
            state_counts[pig.behavior_state.value] += 1
        dist = " ".join(f"{s}={c}" for s, c in state_counts.most_common())
        lines.append(f"  STATES: {dist}")

        # Population summary
        adults = [p for p in pigs if not p.is_baby]
        babies = [p for p in pigs if p.is_baby]
        males = sum(1 for p in pigs if p.gender == Gender.MALE)
        females = sum(1 for p in pigs if p.gender == Gender.FEMALE)
        pregnant = sum(1 for p in pigs if p.is_pregnant)
        breedable = sum(1 for p in pigs if p.can_breed)
        lines.append(
            f"  POP: {len(pigs)} total ({len(adults)} adult, {len(babies)} baby)"
            f" | {males}M/{females}F | {pregnant} pregnant | {breedable} breedable"
        )

        # Breeding program summary
        if state.breeding_program.enabled:
            prog = state.breeding_program
            marked = sum(1 for p in pigs if p.marked_for_sale)
            lines.append(f"  PROGRAM: stock_limit={prog.stock_limit} | marked_for_sale={marked}")

        # Recent game events since last snapshot
        all_events = state.events
        new_events = all_events[self._last_event_count:]
        self._last_event_count = len(all_events)
        if new_events:
            for ev in new_events[-10:]:  # Cap at 10 most recent
                lines.append(f"  EVENT: {ev}")

        for pig in pigs:
            n = pig.needs
            target = pig.target_description or "None"
            fac_id = pig.target_facility_id.hex[:8] if pig.target_facility_id else "-"
            blocked = controller._blocked_timers.get(pig.id, 0)
            failed = controller.facility_manager.get_failed_facilities(pig.id)
            failed_str = ",".join(
                _facility_short_name(state, fid) for fid in failed
            ) if failed else "-"

            lines.append(
                f"  {pig.name:<12} | {pig.behavior_state.value:<12} "
                f"| pos=({pig.position.x:5.1f},{pig.position.y:5.1f}) "
                f"| path={len(pig.path):<3} | fac={fac_id} "
                f"| H={n.hunger:4.0f} T={n.thirst:4.0f} E={n.energy:4.0f} "
                f"Hp={n.happiness:4.0f} S={n.social:4.0f} B={n.boredom:4.0f} "
                f"| blk={blocked:.1f}s | fail=[{failed_str}]"
            )
            lines.append(f"               | target: {target}")

            # Show new behavior log entries since last snapshot
            prev_len = self._last_logs.get(pig.id, 0)
            new_entries = pig.behavior_log[prev_len:]
            self._last_logs[pig.id] = len(pig.behavior_log)
            for entry in new_entries:
                lines.append(f"               |   > {entry}")

        # Compact facility state
        for f in state.get_facilities_list():
            empty = " EMPTY" if f.is_empty else ""
            lines.append(
                f"  FAC {f.name:<16} ({f.position_x:2},{f.position_y:2}) "
                f"| {f.current_amount:5.1f}/{f.max_amount:5.1f}{empty}"
            )

        lines.append("")

        with open(self.path, "a") as fh:
            fh.write("\n".join(lines) + "\n")

        self._truncate_if_needed()

    def _truncate_if_needed(self) -> None:
        try:
            size = self.path.stat().st_size
        except OSError:
            return
        if size <= self.MAX_FILE_SIZE:
            return

        content = self.path.read_text()
        # Keep the last ~75% — find the next snapshot boundary after the cut point
        cut = len(content) // 4
        boundary = content.find("\n--- TICK", cut)
        if boundary > 0:
            self.path.write_text(
                "... (earlier output truncated) ...\n" + content[boundary:]
            )


def _facility_short_name(state: GameState, facility_id: UUID) -> str:
    fac = state.get_facility(facility_id)
    if fac:
        return f"{fac.name}[{facility_id.hex[:4]}]"
    return f"?[{facility_id.hex[:4]}]"
