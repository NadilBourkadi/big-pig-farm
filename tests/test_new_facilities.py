"""Tests for the 5 new facility types and their mechanics."""

from big_pig_farm.data.config import ECONOMY
from big_pig_farm.economy.shop import SHOP_ITEMS, get_shop_items, purchase_item
from big_pig_farm.entities.facilities import FACILITY_INFO, Facility, FacilityType
from big_pig_farm.entities.genetics import Genotype, calculate_phenotype
from big_pig_farm.entities.guinea_pig import BehaviorState, Gender, GuineaPig, Position
from big_pig_farm.game.state import GameState
from big_pig_farm.simulation.auto_resources import (
    STAGE_AUDIENCE_HAPPINESS_PER_HOUR,
    STAGE_AUDIENCE_SOCIAL_PER_HOUR,
    tick_aoe_facilities,
)


def _make_pig(x: float = 5.0, y: float = 5.0) -> GuineaPig:
    """Create a test pig at the given position."""
    genotype = Genotype.random()
    phenotype = calculate_phenotype(genotype)
    return GuineaPig(
        name="TestPig",
        genotype=genotype,
        phenotype=phenotype,
        gender=Gender.MALE,
        position=Position(x=x, y=y),
    )


class TestFacilityData:
    """Tests for new facility type definitions and shop items."""

    def test_all_new_types_have_info(self):
        new_types = [
            FacilityType.FEAST_TABLE,
            FacilityType.CAMPFIRE,
            FacilityType.THERAPY_GARDEN,
            FacilityType.HOT_SPRING,
            FacilityType.STAGE,
        ]
        for facility_type in new_types:
            assert facility_type in FACILITY_INFO, f"{facility_type} missing from FACILITY_INFO"

    def test_all_new_types_have_shop_items(self):
        shop_ids = {item.id for item in SHOP_ITEMS}
        expected = {"feast_table", "campfire", "therapy_garden", "hot_spring", "stage"}
        assert expected.issubset(shop_ids)

    def test_feast_table_is_consumable(self):
        info = FACILITY_INFO[FacilityType.FEAST_TABLE]
        assert info.capacity == 300

    def test_campfire_is_social(self):
        info = FACILITY_INFO[FacilityType.CAMPFIRE]
        assert info.social_bonus > 0
        assert info.happiness_bonus > 0

    def test_therapy_garden_has_high_happiness_bonus(self):
        info = FACILITY_INFO[FacilityType.THERAPY_GARDEN]
        assert info.happiness_bonus == 0.20
        assert info.health_bonus == 0.08

    def test_hot_spring_is_multi_need(self):
        info = FACILITY_INFO[FacilityType.HOT_SPRING]
        assert info.happiness_bonus > 0
        assert info.health_bonus > 0
        assert info.social_bonus > 0

    def test_stage_capacity_is_one(self):
        info = FACILITY_INFO[FacilityType.STAGE]
        assert info.capacity == 1

    def test_facility_costs_match_config(self):
        cost_map = {
            "feast_table": ECONOMY.FEAST_TABLE_COST,
            "campfire": ECONOMY.CAMPFIRE_COST,
            "therapy_garden": ECONOMY.THERAPY_GARDEN_COST,
            "hot_spring": ECONOMY.HOT_SPRING_COST,
            "stage": ECONOMY.STAGE_COST,
        }
        for item in SHOP_ITEMS:
            if item.id in cost_map:
                assert item.cost == cost_map[item.id], f"{item.id} cost mismatch"

    def test_purchase_feast_table(self):
        state = GameState()
        state.money = 10000
        state.farm_tier = 2
        item = next(i for i in get_shop_items(farm_tier=2) if i.id == "feast_table")
        assert purchase_item(state, item, position=(5, 5))
        assert len(state.facilities) == 1

    def test_tier_gating(self):
        """Higher-tier facilities shouldn't be available at lower tiers."""
        tier1_items = get_shop_items(farm_tier=1)
        tier1_ids = {i.id for i in tier1_items if i.unlocked}
        assert "campfire" not in tier1_ids  # Tier 3
        assert "hot_spring" not in tier1_ids  # Tier 4


class TestFeastTable:
    """Tests for Feast Table communal eating mechanics."""

    def test_feast_table_creates_with_capacity(self):
        table = Facility.create(FacilityType.FEAST_TABLE, 5, 5)
        assert table.max_amount == 300
        assert table.current_amount == 300

    def test_feast_table_is_consumable(self):
        table = Facility.create(FacilityType.FEAST_TABLE, 5, 5)
        consumed = table.consume(10.0)
        assert consumed == 10.0
        assert table.current_amount == 290.0


class TestStageAoE:
    """Tests for Stage audience AoE effects."""

    def test_stage_audience_gets_bonuses(self):
        state = GameState()
        stage = Facility.create(FacilityType.STAGE, 10, 10)
        state.add_facility(stage)

        # Performer pig at the stage
        performer = _make_pig(x=11.0, y=12.0)
        performer.behavior_state = BehaviorState.PLAYING
        performer.target_facility_id = stage.id
        state.add_guinea_pig(performer)

        # Audience pig within 6 cells
        audience = _make_pig(x=13.0, y=13.0)
        audience.needs.happiness = 50.0
        audience.needs.social = 50.0
        state.add_guinea_pig(audience)

        game_hours = 1.0
        tick_aoe_facilities(state, game_hours)

        assert audience.needs.happiness > 50.0
        assert audience.needs.social > 50.0

    def test_stage_performer_not_double_buffed(self):
        state = GameState()
        stage = Facility.create(FacilityType.STAGE, 10, 10)
        state.add_facility(stage)

        performer = _make_pig(x=11.0, y=12.0)
        performer.behavior_state = BehaviorState.PLAYING
        performer.target_facility_id = stage.id
        performer.needs.happiness = 50.0
        performer.needs.social = 50.0
        state.add_guinea_pig(performer)

        tick_aoe_facilities(state, game_hours=1.0)

        # Performer should NOT get audience bonuses
        assert performer.needs.happiness == 50.0
        assert performer.needs.social == 50.0

    def test_stage_no_effect_without_performer(self):
        state = GameState()
        stage = Facility.create(FacilityType.STAGE, 10, 10)
        state.add_facility(stage)

        # Pig near stage but no performer
        pig = _make_pig(x=12.0, y=12.0)
        pig.needs.happiness = 50.0
        state.add_guinea_pig(pig)

        tick_aoe_facilities(state, game_hours=1.0)

        assert pig.needs.happiness == 50.0  # Unchanged

    def test_stage_audience_out_of_range(self):
        state = GameState()
        stage = Facility.create(FacilityType.STAGE, 10, 10)
        state.add_facility(stage)

        performer = _make_pig(x=11.0, y=12.0)
        performer.behavior_state = BehaviorState.PLAYING
        performer.target_facility_id = stage.id
        state.add_guinea_pig(performer)

        # Far pig — outside 6-cell radius
        far_pig = _make_pig(x=30.0, y=30.0)
        far_pig.needs.happiness = 50.0
        state.add_guinea_pig(far_pig)

        tick_aoe_facilities(state, game_hours=1.0)

        assert far_pig.needs.happiness == 50.0  # Unchanged

    def test_stage_audience_bonus_amounts(self):
        state = GameState()
        stage = Facility.create(FacilityType.STAGE, 10, 10)
        state.add_facility(stage)

        performer = _make_pig(x=11.0, y=12.0)
        performer.behavior_state = BehaviorState.PLAYING
        performer.target_facility_id = stage.id
        state.add_guinea_pig(performer)

        audience = _make_pig(x=12.0, y=12.0)
        audience.needs.happiness = 0.0
        audience.needs.social = 0.0
        state.add_guinea_pig(audience)

        tick_aoe_facilities(state, game_hours=1.0)

        assert audience.needs.happiness == STAGE_AUDIENCE_HAPPINESS_PER_HOUR
        assert audience.needs.social == STAGE_AUDIENCE_SOCIAL_PER_HOUR


class TestTherapyGarden:
    """Tests for Therapy Garden happiness-gated attraction."""

    def test_therapy_garden_has_correct_bonuses(self):
        info = FACILITY_INFO[FacilityType.THERAPY_GARDEN]
        assert info.happiness_bonus == 0.20
        assert info.health_bonus == 0.08
        assert info.capacity == 2


class TestHotSpring:
    """Tests for Hot Spring multi-need mechanics."""

    def test_hot_spring_has_correct_bonuses(self):
        info = FACILITY_INFO[FacilityType.HOT_SPRING]
        assert info.happiness_bonus == 0.08
        assert info.health_bonus == 0.05
        assert info.social_bonus == 0.10
        assert info.capacity == 4


class TestCampfire:
    """Tests for Campfire nighttime gating."""

    def test_campfire_has_correct_bonuses(self):
        info = FACILITY_INFO[FacilityType.CAMPFIRE]
        assert info.social_bonus == 0.15
        assert info.happiness_bonus == 0.10
        assert info.capacity == 3
