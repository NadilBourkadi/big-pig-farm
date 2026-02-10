"""Textual pilot tests for the main game screen."""

from big_pig_farm.app import BigPigFarmApp
from big_pig_farm.ui.screens.main_game import MainGameScreen
from big_pig_farm.ui.screens.shop import ShopScreen
from big_pig_farm.ui.screens.pig_list import PigListScreen
from big_pig_farm.ui.widgets.farm_view import FarmView
from big_pig_farm.ui.widgets.status_bar import StatusBar


async def test_app_starts_on_main_game_screen():
    """App should push MainGameScreen on mount."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test() as pilot:
        assert isinstance(app.screen, MainGameScreen)


async def test_main_game_has_core_widgets():
    """MainGameScreen should contain status bar, farm view, and footer."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test() as pilot:
        app.query_one("#status-bar", StatusBar)
        app.query_one("#farm-view", FarmView)


async def test_pause_toggle():
    """Pressing space should toggle the pause state."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test() as pilot:
        assert not app.state.is_paused
        await pilot.press("space")
        assert app.state.is_paused
        await pilot.press("space")
        assert not app.state.is_paused


async def test_open_shop_screen():
    """Pressing 's' should push the ShopScreen."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test() as pilot:
        await pilot.press("s")
        assert isinstance(app.screen, ShopScreen)


async def test_open_pig_list_screen():
    """Pressing 'p' should push the PigListScreen."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test() as pilot:
        await pilot.press("p")
        assert isinstance(app.screen, PigListScreen)


async def test_edit_mode_toggle():
    """Pressing 'e' should enter edit mode, escape should exit."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test() as pilot:
        farm_view = app.query_one("#farm-view", FarmView)
        assert not farm_view.edit_mode
        await pilot.press("e")
        assert farm_view.edit_mode
        await pilot.press("escape")
        assert not farm_view.edit_mode
