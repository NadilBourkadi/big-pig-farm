"""Textual pilot tests for the shop screen."""

from textual.widgets import ListView

from big_pig_farm.app import BigPigFarmApp
from big_pig_farm.economy.shop import ShopCategory
from big_pig_farm.ui.screens.main_game import MainGameScreen
from big_pig_farm.ui.screens.shop import ShopScreen


async def test_shop_opens_with_facilities_category():
    """Shop should default to FACILITIES category."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test() as pilot:
        await pilot.press("s")
        screen = app.query_one(ShopScreen)
        assert screen.current_category == ShopCategory.FACILITIES


async def test_shop_category_switching():
    """Pressing category keys should switch categories."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test() as pilot:
        await pilot.press("s")
        screen = app.query_one(ShopScreen)

        await pilot.press("d")
        assert screen.current_category == ShopCategory.PERKS

        await pilot.press("u")
        assert screen.current_category == ShopCategory.UPGRADES

        await pilot.press("a")
        assert screen.current_category == ShopCategory.ADOPTION

        await pilot.press("f")
        assert screen.current_category == ShopCategory.FACILITIES


async def test_shop_has_item_list():
    """Shop should have a ListView with items."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test() as pilot:
        await pilot.press("s")
        list_view = app.query_one("#item-list", ListView)
        assert len(list_view.children) > 0


async def test_shop_escape_goes_back():
    """Pressing escape in shop should return to main game."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("s")
        assert isinstance(app.screen, ShopScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, MainGameScreen)
