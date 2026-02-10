"""Textual pilot tests for the pig list screen."""

from textual.widgets import DataTable

from big_pig_farm.app import BigPigFarmApp
from big_pig_farm.ui.screens.main_game import MainGameScreen
from big_pig_farm.ui.screens.pig_list import PigListScreen


async def test_pig_list_opens():
    """Pressing 'p' should open the pig list screen."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test() as pilot:
        await pilot.press("p")
        assert isinstance(app.screen, PigListScreen)


async def test_pig_list_has_table():
    """Pig list should contain a DataTable."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test() as pilot:
        await pilot.press("p")
        table = app.query_one("#pig-table", DataTable)
        assert table is not None


async def test_pig_table_has_correct_columns():
    """DataTable should have the expected columns."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test() as pilot:
        await pilot.press("p")
        table = app.query_one("#pig-table", DataTable)
        column_labels = [col.label.plain for col in table.columns.values()]
        assert "Name" in column_labels
        assert "Age" in column_labels
        assert "Gender" in column_labels
        assert "Value" in column_labels


async def test_pig_table_shows_starter_pigs():
    """Table row count should match the pig count in game state."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test() as pilot:
        await pilot.press("p")
        table = app.query_one("#pig-table", DataTable)
        assert table.row_count == app.state.pig_count
        assert table.row_count >= 2  # At least the starter pigs


async def test_pig_list_escape_goes_back():
    """Pressing escape should return to the main game screen."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test() as pilot:
        await pilot.press("p")
        assert isinstance(app.screen, PigListScreen)
        await pilot.press("escape")
        assert isinstance(app.screen, MainGameScreen)
