"""Tests for the shop/purchase system."""


from big_pig_farm.data.config import ECONOMY
from big_pig_farm.economy.shop import (
    SHOP_ITEMS,
    check_tier_requirements,
    get_facility_cost,
    get_farm_upgrade_info,
    get_next_tier_upgrade,
    get_shop_items,
    purchase_item,
    purchase_tier_upgrade,
    sell_facility,
)
from big_pig_farm.entities.facilities import Facility, FacilityType
from big_pig_farm.game.state import GameState


class TestShopItems:
    """Tests for shop item definitions."""

    def test_shop_has_items(self):
        assert len(SHOP_ITEMS) > 0

    def test_all_items_have_positive_cost(self):
        for item in SHOP_ITEMS:
            assert item.cost > 0, f"{item.id} has non-positive cost"

    def test_all_facility_items_have_type(self):
        for item in SHOP_ITEMS:
            if item.category.value == "facilities":
                assert item.facility_type is not None, f"{item.id} missing facility_type"


class TestGetShopItems:
    """Tests for available items filtering."""

    def test_tier1_items_available(self):
        items = get_shop_items(farm_tier=1)
        tier1_ids = {i.id for i in items if i.required_tier <= 1}
        assert "food_bowl" in tier1_ids
        assert "water_bottle" in tier1_ids

    def test_items_show_unlock_status(self):
        items = get_shop_items(farm_tier=1)
        for item in items:
            if item.required_tier <= 1:
                assert item.unlocked is True
            else:
                assert item.unlocked is False

    def test_higher_tier_unlocks_more(self):
        tier1_unlocked = [i for i in get_shop_items(farm_tier=1) if i.unlocked]
        tier3_unlocked = [i for i in get_shop_items(farm_tier=3) if i.unlocked]
        assert len(tier3_unlocked) >= len(tier1_unlocked)


class TestPurchaseItem:
    """Tests for purchasing items."""

    def test_purchase_facility(self):
        state = GameState()
        state.money = 10000
        food_bowl = next(i for i in SHOP_ITEMS if i.id == "food_bowl")
        # Unlock it
        food_bowl_copy = type(food_bowl)(
            id=food_bowl.id, name=food_bowl.name, description=food_bowl.description,
            cost=food_bowl.cost, category=food_bowl.category,
            facility_type=food_bowl.facility_type, unlocked=True,
            required_tier=food_bowl.required_tier,
        )

        initial_money = state.money
        result = purchase_item(state, food_bowl_copy, position=(3, 3))
        assert result is True
        assert state.money == initial_money - food_bowl.cost
        assert len(state.facilities) == 1

    def test_cannot_afford(self):
        state = GameState()
        state.money = 0
        food_bowl = next(i for i in SHOP_ITEMS if i.id == "food_bowl")
        food_bowl_copy = type(food_bowl)(
            id=food_bowl.id, name=food_bowl.name, description=food_bowl.description,
            cost=food_bowl.cost, category=food_bowl.category,
            facility_type=food_bowl.facility_type, unlocked=True,
            required_tier=food_bowl.required_tier,
        )
        result = purchase_item(state, food_bowl_copy, position=(3, 3))
        assert result is False
        assert state.money == 0

    def test_locked_item_cannot_purchase(self):
        state = GameState()
        state.money = 10000
        food_bowl = next(i for i in SHOP_ITEMS if i.id == "food_bowl")
        locked_item = type(food_bowl)(
            id=food_bowl.id, name=food_bowl.name, description=food_bowl.description,
            cost=food_bowl.cost, category=food_bowl.category,
            facility_type=food_bowl.facility_type, unlocked=False,
            required_tier=food_bowl.required_tier,
        )
        result = purchase_item(state, locked_item, position=(3, 3))
        assert result is False


class TestSellFacility:
    """Tests for selling/removing facilities."""

    def test_sell_refunds_cost(self):
        state = GameState()
        facility = Facility.create(FacilityType.FOOD_BOWL, 3, 3)
        state.add_facility(facility)
        initial_money = state.money

        refund = sell_facility(state, facility)
        expected_cost = get_facility_cost(FacilityType.FOOD_BOWL)
        assert refund == expected_cost
        assert state.money == initial_money + expected_cost

    def test_sell_removes_facility(self):
        state = GameState()
        facility = Facility.create(FacilityType.FOOD_BOWL, 3, 3)
        state.add_facility(facility)
        assert len(state.facilities) == 1

        sell_facility(state, facility)
        assert len(state.facilities) == 0


class TestGetFacilityCost:
    """Tests for facility cost lookup."""

    def test_known_facility_cost(self):
        cost = get_facility_cost(FacilityType.FOOD_BOWL)
        assert cost == ECONOMY.FOOD_BOWL_COST

    def test_unknown_facility_returns_zero(self):
        # Use a type that's not in SHOP_ITEMS (unlikely but defensive)
        cost = get_facility_cost("nonexistent_type")
        assert cost == 0


class TestTierUpgrade:
    """Tests for the tier upgrade system."""

    def test_next_tier_from_tier1(self):
        state = GameState()
        upgrade = get_next_tier_upgrade(state)
        assert upgrade is not None
        assert upgrade.tier == 2
        assert upgrade.name == "Apprentice"

    def test_no_next_tier_at_max(self):
        state = GameState()
        state.farm_tier = 5
        assert get_next_tier_upgrade(state) is None

    def test_requirements_not_met(self):
        state = GameState()
        upgrade = get_next_tier_upgrade(state)
        reqs = check_tier_requirements(state, upgrade)
        assert not reqs["pigs_born"]
        assert not reqs["pigdex"]

    def test_requirements_met(self):
        state = GameState()
        state.money = 10000
        state.total_pigs_born = 3
        state.pigdex.discovered = {"key1": 1, "key2": 1}
        upgrade = get_next_tier_upgrade(state)
        reqs = check_tier_requirements(state, upgrade)
        assert all(reqs.values())

    def test_purchase_tier_upgrade_success(self):
        state = GameState()
        state.money = 10000
        state.total_pigs_born = 3
        state.pigdex.discovered = {"key1": 1, "key2": 1}
        assert purchase_tier_upgrade(state)
        assert state.farm_tier == 2
        assert state.money == 10000 - 300

    def test_purchase_tier_upgrade_fails_without_requirements(self):
        state = GameState()
        state.money = 10000
        assert not purchase_tier_upgrade(state)
        assert state.farm_tier == 1

    def test_purchase_tier_upgrade_fails_without_money(self):
        state = GameState()
        state.money = 0
        state.total_pigs_born = 3
        state.pigdex.discovered = {"key1": 1, "key2": 1}
        assert not purchase_tier_upgrade(state)
        assert state.farm_tier == 1


class TestRoomCap:
    """Tests for room cap enforcement per tier."""

    def test_tier1_allows_one_room(self):
        state = GameState()
        # Starter has 1 room, tier 1 cap is 1
        assert get_farm_upgrade_info(state) is None

    def test_tier2_allows_second_room(self):
        state = GameState()
        state.farm_tier = 2
        # Starter has 1 room, tier 2 cap is 2
        info = get_farm_upgrade_info(state)
        assert info is not None

    def test_tier2_blocks_third_room(self):
        state = GameState()
        state.farm_tier = 2
        from big_pig_farm.entities.biomes import BiomeType
        state.farm.add_room(BiomeType.MEADOW)
        # Now has 2 rooms, tier 2 cap is 2
        assert get_farm_upgrade_info(state) is None
