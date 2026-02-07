"""Debug logger that writes periodic game state snapshots to a file."""

from datetime import datetime
from pathlib import Path
from uuid import UUID

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
        # Start fresh each session
        self.path.write_text(
            f"=== Debug session started {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n"
        )

    def tick(self, state: GameState, controller: BehaviorController) -> None:
        """Called every simulation tick. Writes a snapshot every SNAPSHOT_INTERVAL ticks."""
        self._total_ticks += 1
        self._tick_counter += 1
        if self._tick_counter < self.SNAPSHOT_INTERVAL:
            return
        self._tick_counter = 0
        self._write_snapshot(state, controller)

    def _write_snapshot(self, state: GameState, controller: BehaviorController) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        lines = [f"--- TICK {self._total_ticks} | {now} | speed={state.speed.value}x ---"]

        for pig in state.get_pigs_list():
            n = pig.needs
            target = pig.target_description or "None"
            fac_id = pig.target_facility_id.hex[:8] if pig.target_facility_id else "-"
            blocked = controller._blocked_timers.get(pig.id, 0)
            failed = controller._failed_facilities.get(pig.id, set())
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
