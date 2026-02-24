"""Tests for SaveManagerV2 (JSON blob) and CombinedSaveManager."""

import sqlite3

import pytest

from big_pig_farm.data.config import GameSpeed
from big_pig_farm.entities.facilities import Facility, FacilityType
from big_pig_farm.entities.guinea_pig import Gender, GuineaPig, Position
from big_pig_farm.game.save_manager_v2 import SCHEMA_VERSION, CombinedSaveManager, SaveManagerV2
from big_pig_farm.game.state import GameState


@pytest.fixture
def tmp_save_path(tmp_path):
    return tmp_path / "test_save_v2.db"


def _make_pig(name="Test", gender=Gender.MALE, age_days=5.0) -> GuineaPig:
    return GuineaPig.create(
        name=name,
        gender=gender,
        position=Position(x=5.0, y=5.0),
        age_days=age_days,
    )


class TestSaveManagerV2:
    """Tests for the JSON blob save manager."""

    def test_roundtrip_empty_state(self, tmp_save_path):
        mgr = SaveManagerV2(tmp_save_path)
        state = GameState()
        mgr.save(state)

        loaded = mgr.load()
        assert loaded is not None
        assert loaded.money == state.money
        assert loaded.pig_count == 0

    def test_roundtrip_with_pigs(self, tmp_save_path):
        mgr = SaveManagerV2(tmp_save_path)
        state = GameState()
        pig = _make_pig()
        state.add_guinea_pig(pig)

        mgr.save(state)
        loaded = mgr.load()

        assert loaded is not None
        assert loaded.pig_count == 1
        rpig = loaded.get_pigs_list()[0]
        assert rpig.name == pig.name
        assert rpig.position.x == pig.position.x
        assert rpig.needs.health == pig.needs.health

    def test_roundtrip_with_facilities(self, tmp_save_path):
        mgr = SaveManagerV2(tmp_save_path)
        state = GameState()
        fac = Facility.create(FacilityType.FOOD_BOWL, 5, 3)
        state.add_facility(fac)

        mgr.save(state)
        loaded = mgr.load()

        assert loaded is not None
        assert len(loaded.get_facilities_list()) == 1
        rfac = loaded.get_facilities_list()[0]
        assert rfac.facility_type == FacilityType.FOOD_BOWL
        assert rfac.position_x == 5
        assert rfac.position_y == 3

    def test_roundtrip_money_and_speed(self, tmp_save_path):
        mgr = SaveManagerV2(tmp_save_path)
        state = GameState()
        state.money = 999
        state.speed = GameSpeed.FAST

        mgr.save(state)
        loaded = mgr.load()

        assert loaded is not None
        assert loaded.money == 999
        assert loaded.speed == GameSpeed.FAST

    def test_roundtrip_statistics(self, tmp_save_path):
        mgr = SaveManagerV2(tmp_save_path)
        state = GameState()
        state.total_pigs_born = 10
        state.total_pigs_sold = 5
        state.total_earnings = 500

        mgr.save(state)
        loaded = mgr.load()

        assert loaded.total_pigs_born == 10
        assert loaded.total_pigs_sold == 5
        assert loaded.total_earnings == 500

    def test_roundtrip_farm_grid(self, tmp_save_path):
        mgr = SaveManagerV2(tmp_save_path)
        state = GameState()

        mgr.save(state)
        loaded = mgr.load()

        assert loaded.farm.width == state.farm.width
        assert loaded.farm.height == state.farm.height
        assert loaded.farm_tier == state.farm_tier
        # Verify pathfinding still works after reload
        walkable = loaded.farm.find_random_walkable()
        assert walkable is not None

    def test_load_nonexistent_returns_none(self, tmp_path):
        mgr = SaveManagerV2(tmp_path / "nonexistent.db")
        assert mgr.load() is None

    def test_has_save(self, tmp_save_path):
        mgr = SaveManagerV2(tmp_save_path)
        assert not mgr.has_save()

        state = GameState()
        mgr.save(state)
        assert mgr.has_save()

    def test_delete_save(self, tmp_save_path):
        mgr = SaveManagerV2(tmp_save_path)
        state = GameState()
        mgr.save(state)
        assert tmp_save_path.exists()

        mgr.delete_save()
        assert not tmp_save_path.exists()

    def test_backup_created(self, tmp_save_path):
        mgr = SaveManagerV2(tmp_save_path)
        state = GameState()
        mgr.save(state)  # First save
        mgr.save(state)  # Second save creates backup

        backup = tmp_save_path.with_suffix(".db.bak")
        assert backup.exists()

    def test_load_corrupted_json_returns_none(self, tmp_save_path):
        """Corrupted JSON blob in the database should return None, not crash."""
        mgr = SaveManagerV2(tmp_save_path)
        # Init the database schema, then insert garbage JSON
        conn = sqlite3.connect(str(tmp_save_path))
        conn.execute(
            "INSERT OR REPLACE INTO game_state_v2 (id, schema_version, json_blob) VALUES (1, ?, ?)",
            (SCHEMA_VERSION, "{not valid json!!!"),
        )
        conn.commit()
        conn.close()

        assert mgr.load() is None


class TestCombinedSaveManager:
    """Tests for the v1→v2 migration manager."""

    def test_v2_save_and_load(self, tmp_save_path):
        mgr = CombinedSaveManager(tmp_save_path)
        state = GameState()
        pig = _make_pig()
        state.add_guinea_pig(pig)

        mgr.save(state)
        loaded = mgr.load()

        assert loaded is not None
        assert loaded.pig_count == 1

    def test_delete_save(self, tmp_save_path):
        mgr = CombinedSaveManager(tmp_save_path)
        state = GameState()
        mgr.save(state)
        assert tmp_save_path.exists()

        mgr.delete_save()
        assert not tmp_save_path.exists()
