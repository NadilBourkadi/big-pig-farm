"""Modernized save/load using Pydantic JSON serialization.

Stores the entire GameState as a single JSON blob in SQLite, replacing
the manual 644-line column-by-column serialization of save_manager.py.
"""

import logging
import shutil
import sqlite3
from pathlib import Path

from big_pig_farm.data.config import TIER_UPGRADES
from big_pig_farm.game.save_manager import SaveManager, get_save_path
from big_pig_farm.game.state import GameState
from big_pig_farm.game.world import relayout_areas

logger = logging.getLogger(__name__)

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
                state.farm._create_legacy_starter_area()
            elif not relayout_areas(state):
                # relayout_areas already rebuilds everything when it fires;
                # only run repair + tunnel rebuild when it was a no-op
                state.farm._repair_area_cells()
                state.farm._rebuild_tunnels()

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
    """Tries v2 load first, falls back to v1. Always saves as v2.

    This allows seamless migration from the old save format to the new one.
    After one save cycle, all future loads will use v2.
    """

    def __init__(self, save_path: Path | None = None):
        path = save_path or get_save_path()
        self.v2 = SaveManagerV2(path)
        self.v1 = SaveManager(path)
        self.save_path = path

    def save(self, state: GameState) -> None:
        """Save using v2 format."""
        self.v2.save(state)

    def save_blob(self, json_blob: str) -> None:
        """Save pre-serialized JSON blob using v2 format."""
        self.v2.save_blob(json_blob)

    def load(self) -> GameState | None:
        """Load from v2 first, fall back to v1."""
        # Try v2 first
        state = self.v2.load()
        if state:
            return state
        # Fall back to v1
        return self.v1.load()

    def delete_save(self) -> None:
        """Delete the save file.

        Unlinks the shared SQLite file directly — both v1 and v2 tables
        live in the same database, so removing the file clears both.
        """
        if self.save_path.exists():
            self.save_path.unlink()
