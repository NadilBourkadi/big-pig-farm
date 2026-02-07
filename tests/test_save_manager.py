"""Tests for save/load round-trip integrity."""

import pytest
from pathlib import Path
from uuid import uuid4

from big_pig_farm.game.save_manager import SaveManager
from big_pig_farm.game.state import GameState
from big_pig_farm.entities.guinea_pig import GuineaPig, Gender, Position
from big_pig_farm.entities.facilities import Facility, FacilityType
from big_pig_farm.entities.pigdex import phenotype_key
from big_pig_farm.data.config import GameSpeed


@pytest.fixture
def tmp_save_path(tmp_path):
    """Create a temporary save path."""
    return tmp_path / "test_save.db"


@pytest.fixture
def save_manager(tmp_save_path):
    """Create a SaveManager with temporary path."""
    return SaveManager(save_path=tmp_save_path)


def _make_pig(name="Test", gender=Gender.MALE, age_days=5.0) -> GuineaPig:
    return GuineaPig.create(
        name=name,
        gender=gender,
        position=Position(x=5.0, y=5.0),
        age_days=age_days,
    )


class TestSaveLoad:
    """Tests for basic save/load round-trip."""

    def test_empty_state_roundtrip(self, save_manager):
        state = GameState()
        save_manager.save(state)
        loaded = save_manager.load()

        assert loaded is not None
        assert loaded.money == state.money
        assert loaded.pig_count == 0

    def test_money_preserved(self, save_manager):
        state = GameState()
        state.money = 12345
        save_manager.save(state)

        loaded = save_manager.load()
        assert loaded.money == 12345

    def test_game_time_preserved(self, save_manager):
        state = GameState()
        state.game_time.day = 42
        state.game_time.hour = 15
        state.game_time.minute = 30
        save_manager.save(state)

        loaded = save_manager.load()
        assert loaded.game_time.day == 42
        assert loaded.game_time.hour == 15
        assert loaded.game_time.minute == 30

    def test_speed_preserved(self, save_manager):
        state = GameState()
        state.speed = GameSpeed.FAST
        save_manager.save(state)

        loaded = save_manager.load()
        assert loaded.speed == GameSpeed.FAST

    def test_statistics_preserved(self, save_manager):
        state = GameState()
        state.total_pigs_born = 10
        state.total_pigs_sold = 5
        state.total_earnings = 500
        save_manager.save(state)

        loaded = save_manager.load()
        assert loaded.total_pigs_born == 10
        assert loaded.total_pigs_sold == 5
        assert loaded.total_earnings == 500


class TestPigPersistence:
    """Tests for guinea pig save/load."""

    def test_pig_roundtrip(self, save_manager):
        state = GameState()
        pig = _make_pig("Bubbles", Gender.FEMALE, age_days=10.5)
        state.add_guinea_pig(pig)
        save_manager.save(state)

        loaded = save_manager.load()
        assert loaded.pig_count == 1
        loaded_pig = loaded.get_pigs_list()[0]
        assert loaded_pig.name == "Bubbles"
        assert loaded_pig.gender == Gender.FEMALE
        assert loaded_pig.age_days == pytest.approx(10.5)

    def test_pig_position_preserved(self, save_manager):
        state = GameState()
        pig = _make_pig()
        pig.position = Position(x=7.5, y=12.3)
        state.add_guinea_pig(pig)
        save_manager.save(state)

        loaded = save_manager.load()
        loaded_pig = loaded.get_pigs_list()[0]
        assert loaded_pig.position.x == pytest.approx(7.5)
        assert loaded_pig.position.y == pytest.approx(12.3)

    def test_pig_needs_preserved(self, save_manager):
        state = GameState()
        pig = _make_pig()
        pig.needs.hunger = 42.0
        pig.needs.thirst = 88.0
        pig.needs.energy = 15.0
        state.add_guinea_pig(pig)
        save_manager.save(state)

        loaded = save_manager.load()
        loaded_pig = loaded.get_pigs_list()[0]
        assert loaded_pig.needs.hunger == pytest.approx(42.0)
        assert loaded_pig.needs.thirst == pytest.approx(88.0)
        assert loaded_pig.needs.energy == pytest.approx(15.0)

    def test_pig_pregnancy_preserved(self, save_manager):
        state = GameState()
        male = _make_pig("Dad", Gender.MALE)
        female = _make_pig("Mom", Gender.FEMALE)
        female.is_pregnant = True
        female.pregnancy_days = 1.5
        female.partner_id = male.id
        state.add_guinea_pig(male)
        state.add_guinea_pig(female)
        save_manager.save(state)

        loaded = save_manager.load()
        loaded_female = [p for p in loaded.get_pigs_list() if p.gender == Gender.FEMALE][0]
        assert loaded_female.is_pregnant is True
        assert loaded_female.pregnancy_days == pytest.approx(1.5)
        assert loaded_female.partner_id == male.id

    def test_pig_breeding_locked_preserved(self, save_manager):
        state = GameState()
        pig = _make_pig()
        pig.breeding_locked = True
        state.add_guinea_pig(pig)
        save_manager.save(state)

        loaded = save_manager.load()
        loaded_pig = loaded.get_pigs_list()[0]
        assert loaded_pig.breeding_locked is True

    def test_pig_origin_tag_preserved(self, save_manager):
        state = GameState()
        pig = _make_pig()
        pig.origin_tag = "Spotted"
        state.add_guinea_pig(pig)
        save_manager.save(state)

        loaded = save_manager.load()
        loaded_pig = loaded.get_pigs_list()[0]
        assert loaded_pig.origin_tag == "Spotted"

    def test_pig_parents_preserved(self, save_manager):
        state = GameState()
        parent_id = uuid4()
        pig = _make_pig()
        pig.mother_id = parent_id
        pig.mother_name = "OldMom"
        pig.father_name = "OldDad"
        state.add_guinea_pig(pig)
        save_manager.save(state)

        loaded = save_manager.load()
        loaded_pig = loaded.get_pigs_list()[0]
        assert loaded_pig.mother_id == parent_id
        assert loaded_pig.mother_name == "OldMom"
        assert loaded_pig.father_name == "OldDad"

    def test_multiple_pigs(self, save_manager):
        state = GameState()
        for i in range(5):
            pig = _make_pig(f"Pig{i}", Gender.MALE if i % 2 == 0 else Gender.FEMALE)
            state.add_guinea_pig(pig)
        save_manager.save(state)

        loaded = save_manager.load()
        assert loaded.pig_count == 5


class TestFacilityPersistence:
    """Tests for facility save/load."""

    def test_facility_roundtrip(self, save_manager):
        state = GameState()
        facility = Facility.create(FacilityType.FOOD_BOWL, 3, 3)
        state.add_facility(facility)
        save_manager.save(state)

        loaded = save_manager.load()
        assert len(loaded.facilities) == 1
        loaded_fac = loaded.get_facilities_list()[0]
        assert loaded_fac.facility_type == FacilityType.FOOD_BOWL
        assert loaded_fac.position_x == 3
        assert loaded_fac.position_y == 3


class TestPigdexPersistence:
    """Tests for pigdex save/load."""

    def test_pigdex_roundtrip(self, save_manager):
        state = GameState()
        pig = _make_pig()
        key = phenotype_key(pig.phenotype)
        state.pigdex.register_phenotype(key, 1)
        save_manager.save(state)

        loaded = save_manager.load()
        assert loaded.pigdex.is_discovered(key)
        assert loaded.pigdex.discovered_count == 1


class TestBackup:
    """Tests for backup functionality."""

    def test_backup_created_on_save(self, save_manager, tmp_save_path):
        state = GameState()
        save_manager.save(state)  # First save
        save_manager.save(state)  # Second save creates backup

        backup_path = tmp_save_path.with_suffix(".db.bak")
        assert backup_path.exists()

    def test_load_returns_none_for_missing_db(self, tmp_path):
        sm = SaveManager(save_path=tmp_path / "nonexistent.db")
        loaded = sm.load()
        # Load should return None for empty DB (no game_state row)
        assert loaded is None
