"""SQLite save/load functionality for game persistence."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from big_pig_farm.game.state import GameState, GameTime, EventLog
from big_pig_farm.entities.guinea_pig import GuineaPig, Gender, BehaviorState, Personality, Needs, Position
from big_pig_farm.entities.genetics import Genotype, Phenotype, calculate_phenotype
from big_pig_farm.entities.facilities import Facility, FacilityType
from big_pig_farm.game.world import FarmGrid


def get_save_path() -> Path:
    """Get the default save file path."""
    # Use user's home directory
    save_dir = Path.home() / ".big_pig_farm"
    save_dir.mkdir(exist_ok=True)
    return save_dir / "savegame.db"


class SaveManager:
    """Manages saving and loading game state to SQLite."""

    def __init__(self, save_path: Optional[Path] = None):
        self.save_path = save_path or get_save_path()
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.save_path) as conn:
            cursor = conn.cursor()

            # Game state table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS game_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    money INTEGER NOT NULL,
                    day INTEGER NOT NULL,
                    hour INTEGER NOT NULL,
                    minute INTEGER NOT NULL,
                    total_game_minutes REAL NOT NULL,
                    last_update TEXT NOT NULL,
                    speed INTEGER NOT NULL,
                    is_paused INTEGER NOT NULL,
                    farm_width INTEGER NOT NULL,
                    farm_height INTEGER NOT NULL,
                    farm_tier INTEGER NOT NULL,
                    total_pigs_born INTEGER NOT NULL,
                    total_pigs_sold INTEGER NOT NULL,
                    total_earnings INTEGER NOT NULL
                )
            """)

            # Guinea pigs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS guinea_pigs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    gender TEXT NOT NULL,
                    age_days REAL NOT NULL,
                    birth_time TEXT NOT NULL,
                    genotype_json TEXT NOT NULL,
                    personality_json TEXT NOT NULL,
                    needs_json TEXT NOT NULL,
                    behavior_state TEXT NOT NULL,
                    position_x REAL NOT NULL,
                    position_y REAL NOT NULL,
                    is_pregnant INTEGER NOT NULL,
                    pregnancy_days REAL NOT NULL,
                    partner_id TEXT,
                    last_birth_time TEXT,
                    mother_id TEXT,
                    father_id TEXT,
                    origin_tag TEXT
                )
            """)

            # Migration: add origin_tag column to existing tables
            try:
                cursor.execute("ALTER TABLE guinea_pigs ADD COLUMN origin_tag TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists

            # Facilities table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facilities (
                    id TEXT PRIMARY KEY,
                    facility_type TEXT NOT NULL,
                    position_x INTEGER NOT NULL,
                    position_y INTEGER NOT NULL,
                    level INTEGER NOT NULL,
                    current_amount REAL NOT NULL,
                    max_amount REAL NOT NULL,
                    auto_refill INTEGER NOT NULL
                )
            """)

            # Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    game_day INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    event_type TEXT NOT NULL
                )
            """)

            # Pigdex tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pigdex (
                    phenotype_key TEXT PRIMARY KEY,
                    discovered_day INTEGER NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pigdex_meta (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    milestones_json TEXT NOT NULL
                )
            """)

            # Contracts tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contracts (
                    id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    required_color TEXT,
                    required_pattern TEXT,
                    required_intensity TEXT,
                    required_roan TEXT,
                    difficulty TEXT NOT NULL,
                    reward INTEGER NOT NULL,
                    deadline_day INTEGER NOT NULL,
                    created_day INTEGER NOT NULL,
                    fulfilled INTEGER NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contract_meta (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    completed_count INTEGER NOT NULL,
                    total_earnings INTEGER NOT NULL,
                    last_refresh_day INTEGER NOT NULL
                )
            """)

            conn.commit()

    def save(self, state: GameState) -> None:
        """Save the current game state."""
        with sqlite3.connect(self.save_path) as conn:
            cursor = conn.cursor()

            # Clear existing data
            cursor.execute("DELETE FROM game_state")
            cursor.execute("DELETE FROM guinea_pigs")
            cursor.execute("DELETE FROM facilities")
            cursor.execute("DELETE FROM events")

            # Save game state
            cursor.execute("""
                INSERT INTO game_state VALUES (
                    1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                state.money,
                state.game_time.day,
                state.game_time.hour,
                state.game_time.minute,
                state.game_time.total_game_minutes,
                state.game_time.last_update.isoformat(),
                state.speed.value,
                1 if state.is_paused else 0,
                state.farm.width,
                state.farm.height,
                state.farm.tier,
                state.total_pigs_born,
                state.total_pigs_sold,
                state.total_earnings,
            ))

            # Save guinea pigs
            for pig in state.guinea_pigs.values():
                cursor.execute("""
                    INSERT INTO guinea_pigs (
                        id, name, gender, age_days, birth_time, genotype_json,
                        personality_json, needs_json, behavior_state,
                        position_x, position_y, is_pregnant, pregnancy_days,
                        partner_id, last_birth_time, mother_id, father_id, origin_tag
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(pig.id),
                    pig.name,
                    pig.gender.value,
                    pig.age_days,
                    pig.birth_time.isoformat(),
                    pig.genotype.model_dump_json(),
                    json.dumps([p.value for p in pig.personality]),
                    pig.needs.model_dump_json(),
                    pig.behavior_state.value,
                    pig.position.x,
                    pig.position.y,
                    1 if pig.is_pregnant else 0,
                    pig.pregnancy_days,
                    str(pig.partner_id) if pig.partner_id else None,
                    pig.last_birth_time.isoformat() if pig.last_birth_time else None,
                    str(pig.mother_id) if pig.mother_id else None,
                    str(pig.father_id) if pig.father_id else None,
                    pig.origin_tag,
                ))

            # Save facilities
            for facility in state.facilities.values():
                cursor.execute("""
                    INSERT INTO facilities VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(facility.id),
                    facility.facility_type.value,
                    facility.position_x,
                    facility.position_y,
                    facility.level,
                    facility.current_amount,
                    facility.max_amount,
                    1 if facility.auto_refill else 0,
                ))

            # Save recent events
            for event in state.events[-50:]:  # Keep last 50 events
                cursor.execute("""
                    INSERT INTO events (timestamp, game_day, message, event_type)
                    VALUES (?, ?, ?, ?)
                """, (
                    event.timestamp.isoformat(),
                    event.game_day,
                    event.message,
                    event.event_type,
                ))

            # Save pigdex
            cursor.execute("DELETE FROM pigdex")
            cursor.execute("DELETE FROM pigdex_meta")
            for key, day in state.pigdex.discovered.items():
                cursor.execute(
                    "INSERT INTO pigdex (phenotype_key, discovered_day) VALUES (?, ?)",
                    (key, day),
                )
            cursor.execute(
                "INSERT INTO pigdex_meta VALUES (1, ?)",
                (json.dumps(state.pigdex.milestone_rewards_claimed),),
            )

            # Save contracts
            cursor.execute("DELETE FROM contracts")
            cursor.execute("DELETE FROM contract_meta")
            if hasattr(state, 'contract_board'):
                board = state.contract_board
                for contract in board.active_contracts:
                    cursor.execute("""
                        INSERT INTO contracts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(contract.id),
                        contract.description,
                        contract.required_color.value if contract.required_color else None,
                        contract.required_pattern.value if contract.required_pattern else None,
                        contract.required_intensity.value if contract.required_intensity else None,
                        contract.required_roan.value if contract.required_roan else None,
                        contract.difficulty.value,
                        contract.reward,
                        contract.deadline_day,
                        contract.created_day,
                        1 if contract.fulfilled else 0,
                    ))
                cursor.execute(
                    "INSERT INTO contract_meta VALUES (1, ?, ?, ?)",
                    (board.completed_contracts, board.total_contract_earnings, board.last_refresh_day),
                )

            conn.commit()

        state.last_save = datetime.now()

    def load(self) -> Optional[GameState]:
        """Load game state from save file."""
        if not self.save_path.exists():
            return None

        try:
            with sqlite3.connect(self.save_path) as conn:
                cursor = conn.cursor()

                # Load game state
                cursor.execute("SELECT * FROM game_state WHERE id = 1")
                row = cursor.fetchone()

                if not row:
                    return None

                from big_pig_farm.data.config import GameSpeed

                try:
                    saved_speed = GameSpeed(row[7])
                except ValueError:
                    saved_speed = GameSpeed.NORMAL

                state = GameState(
                    money=row[1],
                    game_time=GameTime(
                        day=row[2],
                        hour=row[3],
                        minute=row[4],
                        total_game_minutes=row[5],
                        last_update=datetime.fromisoformat(row[6]),
                    ),
                    speed=saved_speed,
                    is_paused=bool(row[8]),
                    farm=FarmGrid(width=row[9], height=row[10], tier=row[11]),
                    total_pigs_born=row[12],
                    total_pigs_sold=row[13],
                    total_earnings=row[14],
                )

                # Load guinea pigs
                cursor.execute("SELECT * FROM guinea_pigs")
                for row in cursor.fetchall():
                    genotype = Genotype.model_validate_json(row[5])
                    phenotype = calculate_phenotype(genotype)
                    personality = [Personality(p) for p in json.loads(row[6])]
                    needs = Needs.model_validate_json(row[7])

                    # origin_tag is column 17, may not exist in old saves
                    origin_tag = row[17] if len(row) > 17 else None

                    pig = GuineaPig(
                        id=UUID(row[0]),
                        name=row[1],
                        gender=Gender(row[2]),
                        age_days=row[3],
                        birth_time=datetime.fromisoformat(row[4]),
                        genotype=genotype,
                        phenotype=phenotype,
                        personality=personality,
                        needs=needs,
                        behavior_state=BehaviorState(row[8]),
                        position=Position(x=row[9], y=row[10]),
                        is_pregnant=bool(row[11]),
                        pregnancy_days=row[12],
                        partner_id=UUID(row[13]) if row[13] else None,
                        last_birth_time=datetime.fromisoformat(row[14]) if row[14] else None,
                        mother_id=UUID(row[15]) if row[15] else None,
                        father_id=UUID(row[16]) if row[16] else None,
                        origin_tag=origin_tag,
                    )
                    state.add_guinea_pig(pig)

                # Load facilities
                cursor.execute("SELECT * FROM facilities")
                for row in cursor.fetchall():
                    facility = Facility(
                        id=UUID(row[0]),
                        facility_type=FacilityType(row[1]),
                        position_x=row[2],
                        position_y=row[3],
                        level=row[4],
                        current_amount=row[5],
                        max_amount=row[6],
                        auto_refill=bool(row[7]),
                    )
                    state.add_facility(facility)

                # Load events
                cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT 50")
                for row in cursor.fetchall():
                    event = EventLog(
                        timestamp=datetime.fromisoformat(row[1]),
                        game_day=row[2],
                        message=row[3],
                        event_type=row[4],
                    )
                    state.events.append(event)

                state.events.reverse()  # Put in chronological order

                # Load pigdex
                try:
                    cursor.execute("SELECT phenotype_key, discovered_day FROM pigdex")
                    for row in cursor.fetchall():
                        state.pigdex.discovered[row[0]] = row[1]

                    cursor.execute("SELECT milestones_json FROM pigdex_meta WHERE id = 1")
                    meta_row = cursor.fetchone()
                    if meta_row:
                        state.pigdex.milestone_rewards_claimed = json.loads(meta_row[0])
                except sqlite3.OperationalError:
                    pass  # Table doesn't exist in old saves

                # Load contracts
                try:
                    from big_pig_farm.economy.contracts import BreedingContract, ContractDifficulty, ContractBoard
                    from big_pig_farm.entities.genetics import BaseColor, Pattern, ColorIntensity, RoanType

                    cursor.execute("SELECT * FROM contracts WHERE fulfilled = 0")
                    contracts = []
                    for row in cursor.fetchall():
                        contract = BreedingContract(
                            id=UUID(row[0]),
                            description=row[1],
                            required_color=BaseColor(row[2]) if row[2] else None,
                            required_pattern=Pattern(row[3]) if row[3] else None,
                            required_intensity=ColorIntensity(row[4]) if row[4] else None,
                            required_roan=RoanType(row[5]) if row[5] else None,
                            difficulty=ContractDifficulty(row[6]),
                            reward=row[7],
                            deadline_day=row[8],
                            created_day=row[9],
                            fulfilled=bool(row[10]),
                        )
                        contracts.append(contract)

                    cursor.execute("SELECT * FROM contract_meta WHERE id = 1")
                    cmeta = cursor.fetchone()
                    if cmeta:
                        state.contract_board.active_contracts = contracts
                        state.contract_board.completed_contracts = cmeta[1]
                        state.contract_board.total_contract_earnings = cmeta[2]
                        state.contract_board.last_refresh_day = cmeta[3]
                except (sqlite3.OperationalError, ImportError):
                    pass  # Table doesn't exist or contracts module not yet available

                # Check if farm needs resizing to match current config
                resized, offset_x, offset_y = state.farm.resize_to_match_config()
                if resized:
                    # Reposition all pigs
                    for pig in state.guinea_pigs.values():
                        pig.position.x += offset_x
                        pig.position.y += offset_y
                        # Clear any paths that would be invalid now
                        pig.path = []
                        pig.target_position = None

                    # Reposition all facilities
                    for facility in state.facilities.values():
                        facility.position_x += offset_x
                        facility.position_y += offset_y

                    # Re-register facilities on the grid
                    for facility in state.facilities.values():
                        state.farm.place_facility(facility)

                return state

        except Exception as e:
            print(f"Error loading save: {e}")
            return None

    def has_save(self) -> bool:
        """Check if a save file exists."""
        return self.save_path.exists()

    def delete_save(self) -> None:
        """Delete the save file."""
        if self.save_path.exists():
            self.save_path.unlink()
