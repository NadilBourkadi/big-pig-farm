"""Save/load using Pydantic JSON serialization.

Stores the entire GameState as a single JSON blob in SQLite.
"""

import logging
import shutil
import sqlite3
from pathlib import Path

from big_pig_farm.data.config import TIER_UPGRADES
from big_pig_farm.game.state import GameState
from big_pig_farm.game.world import relayout_areas, resize_all_rooms

logger = logging.getLogger(__name__)


def get_save_path() -> Path:
    """Get the default save file path."""
    save_dir = Path.home() / ".big_pig_farm"
    save_dir.mkdir(exist_ok=True)
    return save_dir / "savegame.db"

# Schema version to detect future format changes
SCHEMA_VERSION = 2


class SaveManagerV2:
    """Saves and loads GameState as a single JSON blob in SQLite."""

    def __init__(self, save_path: Path):
        self.save_path = save_path
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the v2 database schema."""
        conn = sqlite3.connect(str(self.save_path))
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS game_state_v2 (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    schema_version INTEGER NOT NULL,
                    json_blob TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def save(self, state: GameState) -> None:
        """Save entire game state as JSON."""
        self.save_blob(state.model_dump_json())

    def save_blob(self, json_blob: str) -> None:
        """Save pre-serialized JSON blob to SQLite."""
        # Create backup before writing
        if self.save_path.exists():
            backup = self.save_path.with_suffix(".db.bak")
            shutil.copy2(str(self.save_path), str(backup))

        conn = sqlite3.connect(str(self.save_path))
        try:
            conn.execute(
                """INSERT OR REPLACE INTO game_state_v2 (id, schema_version, json_blob)
                   VALUES (1, ?, ?)""",
                (SCHEMA_VERSION, json_blob),
            )
            conn.commit()
        finally:
            conn.close()

    def load(self) -> GameState | None:
        """Load game state from JSON blob. Returns None if no save exists."""
        if not self.save_path.exists():
            return None

        conn = sqlite3.connect(str(self.save_path))
        try:
            # Check if v2 table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='game_state_v2'"
            )
            if not cursor.fetchone():
                return None

            cursor = conn.execute(
                "SELECT json_blob FROM game_state_v2 WHERE id = 1"
            )
            row = cursor.fetchone()
            if not row:
                return None

            json_blob = row[0]
            state = GameState.model_validate_json(json_blob)

            # Migrate farm_tier from legacy farm.tier for existing saves.
            # Only fire when farm.tier > 1 (indicating legacy auto-increment was used).
            # Grandfathers tier-gated facilities already purchased under the old system.
            if state.farm_tier == 1 and state.farm.tier > 1:
                max_tier = TIER_UPGRADES[-1].tier
                state.farm_tier = min(state.farm.tier, max_tier)

            # Migrate saves from before multi-area support
            if not state.farm.areas:
                state.farm.create_legacy_starter_area()
            elif not relayout_areas(state):
                # relayout_areas already rebuilds everything when it fires;
                # only run repair + tunnel rebuild when it was a no-op
                state.farm.repair_area_cells()
                state.farm.rebuild_tunnels()

            # Sync farm.tier and resize rooms to match current tier dimensions.
            # No-op if dimensions already match (new saves).
            state.farm.tier = state.farm_tier
            resize_all_rooms(state, state.farm_tier)

            return state
        except Exception as e:
            logger.error(f"Failed to load v2 save: {e}")
            return None
        finally:
            conn.close()

    def has_save(self) -> bool:
        """Check if a v2 save exists."""
        if not self.save_path.exists():
            return False
        conn = sqlite3.connect(str(self.save_path))
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='game_state_v2'"
            )
            if not cursor.fetchone():
                return False
            cursor = conn.execute("SELECT COUNT(*) FROM game_state_v2")
            return cursor.fetchone()[0] > 0
        except Exception:
            return False
        finally:
            conn.close()

    def delete_save(self) -> None:
        """Delete the save file."""
        if self.save_path.exists():
            self.save_path.unlink()


class CombinedSaveManager:
    """Thin wrapper around SaveManagerV2 with default path resolution.

    Kept for API compatibility with app.py and tests.
    """

    def __init__(self, save_path: Path | None = None):
        path = save_path or get_save_path()
        self.v2 = SaveManagerV2(path)
        self.save_path = path

    def save(self, state: GameState) -> None:
        """Save using v2 format."""
        self.v2.save(state)

    def save_blob(self, json_blob: str) -> None:
        """Save pre-serialized JSON blob using v2 format."""
        self.v2.save_blob(json_blob)

    def load(self) -> GameState | None:
        """Load game state."""
        return self.v2.load()

    def delete_save(self) -> None:
        """Delete the save file."""
        if self.save_path.exists():
            self.save_path.unlink()
