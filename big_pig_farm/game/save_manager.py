"""SQLite save/load functionality for game persistence."""

import json
import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from big_pig_farm.data.config import GameSpeed
from big_pig_farm.economy.contracts import BreedingContract, ContractDifficulty, ContractBoard
from big_pig_farm.simulation.breeding_program import BreedingProgram, BreedingStrategy
from big_pig_farm.game.state import GameState, GameTime, EventLog, BreedingPair
from big_pig_farm.entities.guinea_pig import GuineaPig, Gender, BehaviorState, Personality, Needs, Position
from big_pig_farm.entities.genetics import Genotype, Phenotype, calculate_phenotype, BaseColor, Pattern, ColorIntensity, RoanType
from big_pig_farm.entities.facilities import Facility, FacilityType
from big_pig_farm.game.world import FarmGrid

logger = logging.getLogger(__name__)


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
                    last_birth_age REAL,
                    mother_id TEXT,
                    father_id TEXT,
                    origin_tag TEXT
                )
            """)

            # Migrations: add columns to existing tables
            for col, typedef in [
                ("origin_tag", "TEXT"),
                ("breeding_locked", "INTEGER DEFAULT 0"),
                ("mother_name", "TEXT"),
                ("father_name", "TEXT"),
                ("last_birth_age", "REAL"),
                ("partner_genotype_json", "TEXT"),
                ("partner_name", "TEXT"),
                ("marked_for_sale", "INTEGER DEFAULT 0"),
            ]:
                try:
                    cursor.execute(f"ALTER TABLE guinea_pigs ADD COLUMN {col} {typedef}")
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

            # Breeding pair table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS breeding_pair (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    male_id TEXT NOT NULL,
                    female_id TEXT NOT NULL
                )
            """)

            # Breeding program table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS breeding_program (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    target_colors_json TEXT NOT NULL,
                    target_patterns_json TEXT NOT NULL,
                    target_intensities_json TEXT NOT NULL,
                    target_roan_json TEXT NOT NULL,
                    keep_carriers INTEGER NOT NULL,
                    auto_pair INTEGER NOT NULL,
                    stock_limit INTEGER NOT NULL,
                    enabled INTEGER NOT NULL
                )
            """)

            # Breeding program migrations
            for col, typedef in [
                ("maximize_diversity", "INTEGER DEFAULT 0"),
                ("strategy", "TEXT DEFAULT 'target'"),
            ]:
                try:
                    cursor.execute(f"ALTER TABLE breeding_program ADD COLUMN {col} {typedef}")
                except sqlite3.OperationalError:
                    pass  # Column already exists

            conn.commit()

    def _backup_save(self) -> None:
        """Create a backup of the current save file before overwriting."""
        if not self.save_path.exists():
            return
        backup_path = self.save_path.with_suffix(".db.bak")
        try:
            shutil.copy2(self.save_path, backup_path)
        except OSError as e:
            logger.warning("Failed to create save backup: %s", e)

    def save(self, state: GameState) -> None:
        """Save the current game state.

        Uses a single transaction so that a crash mid-save cannot corrupt
        the database.  A backup of the previous save is kept as .db.bak.
        """
        self._backup_save()

        conn = sqlite3.connect(self.save_path)
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN")

            # Clear existing data
            cursor.execute("DELETE FROM game_state")
            cursor.execute("DELETE FROM guinea_pigs")
            cursor.execute("DELETE FROM facilities")
            cursor.execute("DELETE FROM events")
            cursor.execute("DELETE FROM pigdex")
            cursor.execute("DELETE FROM pigdex_meta")
            cursor.execute("DELETE FROM contracts")
            cursor.execute("DELETE FROM contract_meta")
            cursor.execute("DELETE FROM breeding_pair")
            cursor.execute("DELETE FROM breeding_program")

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
                        partner_id, last_birth_age, mother_id, father_id,
                        origin_tag, breeding_locked, mother_name, father_name,
                        partner_genotype_json, partner_name, marked_for_sale
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    pig.last_birth_age,
                    str(pig.mother_id) if pig.mother_id else None,
                    str(pig.father_id) if pig.father_id else None,
                    pig.origin_tag,
                    1 if pig.breeding_locked else 0,
                    pig.mother_name,
                    pig.father_name,
                    pig.partner_genotype.model_dump_json() if pig.partner_genotype else None,
                    pig.partner_name,
                    1 if pig.marked_for_sale else 0,
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

            # Save breeding pair
            if state.breeding_pair is not None:
                cursor.execute(
                    "INSERT INTO breeding_pair VALUES (1, ?, ?)",
                    (str(state.breeding_pair.male_id), str(state.breeding_pair.female_id)),
                )

            # Save breeding program
            bp = state.breeding_program
            cursor.execute(
                "INSERT INTO breeding_program VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    json.dumps([c.value for c in bp.target_colors]),
                    json.dumps([p.value for p in bp.target_patterns]),
                    json.dumps([i.value for i in bp.target_intensities]),
                    json.dumps([r.value for r in bp.target_roan]),
                    1 if bp.keep_carriers else 0,
                    1 if bp.auto_pair else 0,
                    bp.stock_limit,
                    1 if bp.enabled else 0,
                    0,  # legacy maximize_diversity column
                    bp.strategy.value,
                ),
            )

            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("Failed to save game")
            raise
        finally:
            conn.close()

        state.last_save = datetime.now()

    def load(self) -> Optional[GameState]:
        """Load game state from save file.

        Uses sqlite3.Row for name-based column access so column order
        changes don't silently corrupt data.
        """
        if not self.save_path.exists():
            return None

        try:
            conn = sqlite3.connect(self.save_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Load game state
            cursor.execute("SELECT * FROM game_state WHERE id = 1")
            row = cursor.fetchone()

            if not row:
                conn.close()
                return None

            try:
                saved_speed = GameSpeed(row["speed"])
            except ValueError:
                saved_speed = GameSpeed.NORMAL

            state = GameState(
                money=row["money"],
                game_time=GameTime(
                    day=row["day"],
                    hour=row["hour"],
                    minute=row["minute"],
                    total_game_minutes=row["total_game_minutes"],
                    last_update=datetime.fromisoformat(row["last_update"]),
                ),
                speed=saved_speed,
                is_paused=bool(row["is_paused"]),
                farm=FarmGrid(width=row["farm_width"], height=row["farm_height"], tier=row["farm_tier"]),
                total_pigs_born=row["total_pigs_born"],
                total_pigs_sold=row["total_pigs_sold"],
                total_earnings=row["total_earnings"],
            )

            # Load guinea pigs
            cursor.execute("SELECT * FROM guinea_pigs")
            for row in cursor.fetchall():
                genotype = Genotype.model_validate_json(row["genotype_json"])
                phenotype = calculate_phenotype(genotype)
                personality = [Personality(p) for p in json.loads(row["personality_json"])]
                needs = Needs.model_validate_json(row["needs_json"])

                # Columns that may not exist in old saves
                row_keys = row.keys()
                origin_tag = row["origin_tag"] if "origin_tag" in row_keys else None
                breeding_locked = bool(row["breeding_locked"]) if "breeding_locked" in row_keys else False
                mother_name = row["mother_name"] if "mother_name" in row_keys else None
                father_name = row["father_name"] if "father_name" in row_keys else None
                last_birth_age = row["last_birth_age"] if "last_birth_age" in row_keys else None

                marked_for_sale = bool(row["marked_for_sale"]) if "marked_for_sale" in row_keys else False

                # Load partner genotype stored at conception (for pregnancy survival)
                partner_genotype = None
                if "partner_genotype_json" in row_keys and row["partner_genotype_json"]:
                    try:
                        partner_genotype = Genotype.model_validate_json(row["partner_genotype_json"])
                    except Exception:
                        pass
                partner_name_stored = row["partner_name"] if "partner_name" in row_keys else None

                pig = GuineaPig(
                    id=UUID(row["id"]),
                    name=row["name"],
                    gender=Gender(row["gender"]),
                    age_days=row["age_days"],
                    birth_time=datetime.fromisoformat(row["birth_time"]),
                    genotype=genotype,
                    phenotype=phenotype,
                    personality=personality,
                    needs=needs,
                    behavior_state=BehaviorState(row["behavior_state"]),
                    position=Position(x=row["position_x"], y=row["position_y"]),
                    is_pregnant=bool(row["is_pregnant"]),
                    pregnancy_days=row["pregnancy_days"],
                    partner_id=UUID(row["partner_id"]) if row["partner_id"] else None,
                    partner_genotype=partner_genotype,
                    partner_name=partner_name_stored,
                    last_birth_age=last_birth_age,
                    mother_id=UUID(row["mother_id"]) if row["mother_id"] else None,
                    father_id=UUID(row["father_id"]) if row["father_id"] else None,
                    origin_tag=origin_tag,
                    breeding_locked=breeding_locked,
                    marked_for_sale=marked_for_sale,
                    mother_name=mother_name,
                    father_name=father_name,
                )
                state.add_guinea_pig(pig)

            # Load facilities
            cursor.execute("SELECT * FROM facilities")
            for row in cursor.fetchall():
                facility = Facility(
                    id=UUID(row["id"]),
                    facility_type=FacilityType(row["facility_type"]),
                    position_x=row["position_x"],
                    position_y=row["position_y"],
                    level=row["level"],
                    current_amount=row["current_amount"],
                    max_amount=row["max_amount"],
                    auto_refill=bool(row["auto_refill"]),
                )
                state.add_facility(facility)

            # Load events
            cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT 50")
            for row in cursor.fetchall():
                event = EventLog(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    game_day=row["game_day"],
                    message=row["message"],
                    event_type=row["event_type"],
                )
                state.events.append(event)

            state.events.reverse()  # Put in chronological order

            # Load pigdex
            try:
                cursor.execute("SELECT phenotype_key, discovered_day FROM pigdex")
                for row in cursor.fetchall():
                    key = row["phenotype_key"]
                    # Migrate old "light_golden" keys to "cream"
                    key = key.replace("light_golden", "cream")
                    state.pigdex.discovered[key] = row["discovered_day"]

                cursor.execute("SELECT milestones_json FROM pigdex_meta WHERE id = 1")
                meta_row = cursor.fetchone()
                if meta_row:
                    state.pigdex.milestone_rewards_claimed = json.loads(meta_row["milestones_json"])
            except sqlite3.OperationalError:
                pass  # Table doesn't exist in old saves

            # Load contracts
            try:
                cursor.execute("SELECT * FROM contracts WHERE fulfilled = 0")
                contracts = []
                for row in cursor.fetchall():
                    # Migrate old "light_golden" color to "cream"
                    raw_color = row["required_color"]
                    if raw_color == "light_golden":
                        raw_color = "cream"
                    contract = BreedingContract(
                        id=UUID(row["id"]),
                        description=row["description"],
                        required_color=BaseColor(raw_color) if raw_color else None,
                        required_pattern=Pattern(row["required_pattern"]) if row["required_pattern"] else None,
                        required_intensity=ColorIntensity(row["required_intensity"]) if row["required_intensity"] else None,
                        required_roan=RoanType(row["required_roan"]) if row["required_roan"] else None,
                        difficulty=ContractDifficulty(row["difficulty"]),
                        reward=row["reward"],
                        deadline_day=row["deadline_day"],
                        created_day=row["created_day"],
                        fulfilled=bool(row["fulfilled"]),
                    )
                    contracts.append(contract)

                cursor.execute("SELECT * FROM contract_meta WHERE id = 1")
                cmeta = cursor.fetchone()
                if cmeta:
                    state.contract_board.active_contracts = contracts
                    state.contract_board.completed_contracts = cmeta["completed_count"]
                    state.contract_board.total_contract_earnings = cmeta["total_earnings"]
                    state.contract_board.last_refresh_day = cmeta["last_refresh_day"]
            except (sqlite3.OperationalError, ImportError):
                pass  # Table doesn't exist or contracts module not yet available

            # Load breeding pair
            try:
                cursor.execute("SELECT male_id, female_id FROM breeding_pair WHERE id = 1")
                breeding_pair_row = cursor.fetchone()
                if breeding_pair_row:
                    male_id = UUID(breeding_pair_row["male_id"])
                    female_id = UUID(breeding_pair_row["female_id"])
                    # Only restore if both pigs still exist
                    if male_id in state.guinea_pigs and female_id in state.guinea_pigs:
                        state.breeding_pair = BreedingPair(male_id=male_id, female_id=female_id)
            except sqlite3.OperationalError:
                pass  # Table doesn't exist in old saves

            # Load breeding program (try new table first, fall back to old breeding_filter)
            try:
                cursor.execute("SELECT * FROM breeding_program WHERE id = 1")
                bp_row = cursor.fetchone()
                if bp_row:
                    bp_keys = bp_row.keys()
                    # Load strategy: prefer new column, fall back to migrating maximize_diversity
                    if "strategy" in bp_keys and bp_row["strategy"]:
                        try:
                            strategy = BreedingStrategy(bp_row["strategy"])
                        except ValueError:
                            strategy = BreedingStrategy.TARGET
                    elif "maximize_diversity" in bp_keys and bool(bp_row["maximize_diversity"]):
                        strategy = BreedingStrategy.DIVERSITY
                    else:
                        strategy = BreedingStrategy.TARGET
                    state.breeding_program = BreedingProgram(
                        target_colors={BaseColor("cream" if v == "light_golden" else v) for v in json.loads(bp_row["target_colors_json"])},
                        target_patterns={Pattern(v) for v in json.loads(bp_row["target_patterns_json"])},
                        target_intensities={ColorIntensity(v) for v in json.loads(bp_row["target_intensities_json"])},
                        target_roan={RoanType(v) for v in json.loads(bp_row["target_roan_json"])},
                        keep_carriers=bool(bp_row["keep_carriers"]),
                        auto_pair=bool(bp_row["auto_pair"]),
                        strategy=strategy,
                        stock_limit=bp_row["stock_limit"],
                        enabled=bool(bp_row["enabled"]),
                    )
            except (sqlite3.OperationalError, Exception):
                # Fall back to old breeding_filter table for migration
                try:
                    cursor.execute("SELECT * FROM breeding_filter WHERE id = 1")
                    bf_row = cursor.fetchone()
                    if bf_row:
                        state.breeding_program = BreedingProgram(
                            target_colors={BaseColor("cream" if v == "light_golden" else v) for v in json.loads(bf_row["keep_colors_json"])},
                            target_patterns={Pattern(v) for v in json.loads(bf_row["keep_patterns_json"])},
                            target_intensities={ColorIntensity(v) for v in json.loads(bf_row["keep_intensities_json"])},
                            target_roan={RoanType(v) for v in json.loads(bf_row["keep_roan_json"])},
                            keep_carriers=bool(bf_row["carrier_aware"]),
                            auto_pair=True,
                            stock_limit=6,
                            enabled=bool(bf_row["enabled"]),
                        )
                except (sqlite3.OperationalError, Exception):
                    pass  # Neither table exists

            conn.close()

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

        except Exception:
            logger.exception("Error loading save file")
            return None

    def has_save(self) -> bool:
        """Check if a save file exists."""
        return self.save_path.exists()

    def delete_save(self) -> None:
        """Delete the save file."""
        if self.save_path.exists():
            self.save_path.unlink()
