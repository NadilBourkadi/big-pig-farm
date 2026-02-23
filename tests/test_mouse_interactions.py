"""Tests for mouse scroll and click interactions in the farm view."""

from textual.events import Click, MouseScrollDown, MouseScrollUp

from big_pig_farm.app import BigPigFarmApp
from big_pig_farm.entities.guinea_pig import Gender, GuineaPig, Position
from big_pig_farm.ui.screens.main_game import MainGameScreen
from big_pig_farm.ui.widgets.farm_view import FarmView


def _add_test_pig(app: BigPigFarmApp, name: str = "Testy", x: float = 10.0, y: float = 10.0) -> GuineaPig:
    """Add a pig to the app's game state and return it."""
    pig = GuineaPig.create(
        name=name,
        gender=Gender.MALE,
        position=Position(x=x, y=y),
        age_days=5.0,
    )
    app.state.add_guinea_pig(pig)
    return pig


def _pig_screen_center(farm_view: FarmView, pig: GuineaPig) -> tuple[int, int]:
    """Compute where a pig's center appears in widget-local coordinates."""
    scale = farm_view._scale()
    farm = farm_view.state.farm
    width = farm_view.size.width
    height = farm_view.size.height
    scaled_w = int(farm.width * scale)
    scaled_h = int(farm.height * scale)
    offset_x = max(0, (width - scaled_w) // 2)
    offset_y = max(0, (height - scaled_h) // 2)
    screen_x = int((pig.position.x - farm_view._viewport_x) * scale) + offset_x
    screen_y = int((pig.position.y - farm_view._viewport_y) * scale) + offset_y
    return screen_x, screen_y


# ------------------------------------------------------------------
# Scroll tests
# ------------------------------------------------------------------


async def test_scroll_down_pans_viewport():
    """Mouse scroll down should increase viewport_y."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test():
        farm_view = app.query_one("#farm-view", FarmView)
        initial_y = farm_view._viewport_y
        farm_view.on_mouse_scroll_down(MouseScrollDown(0, 0, 0, 0, 0, 0, False, False, False))
        assert farm_view._viewport_y > initial_y


async def test_scroll_up_pans_viewport():
    """Mouse scroll up should decrease viewport_y."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test():
        farm_view = app.query_one("#farm-view", FarmView)
        # First scroll down to have room to scroll up
        farm_view.scroll(0, 4)
        y_after_down = farm_view._viewport_y
        farm_view.on_mouse_scroll_up(MouseScrollUp(0, 0, 0, 0, 0, 0, False, False, False))
        assert farm_view._viewport_y < y_after_down


async def test_scroll_breaks_follow_cam():
    """Scrolling while following a pig should stop following."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test() as pilot:
        pig = _add_test_pig(app)
        farm_view = app.query_one("#farm-view", FarmView)
        screen = app.query_one(MainGameScreen)
        screen._follow_pig(pig)
        assert farm_view.selected_pig_id == pig.id

        # Scroll posts ScrollPanned → MainGameScreen._stop_following
        farm_view.on_mouse_scroll_down(MouseScrollDown(0, 0, 0, 0, 0, 0, False, False, False))
        await pilot.pause()
        assert farm_view.selected_pig_id is None


async def test_shift_scroll_pans_horizontally():
    """Shift+scroll should pan the viewport left/right instead of up/down."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test():
        farm_view = app.query_one("#farm-view", FarmView)
        initial_x = farm_view._viewport_x
        initial_y = farm_view._viewport_y
        # shift=True → horizontal pan
        farm_view.on_mouse_scroll_down(MouseScrollDown(0, 0, 0, 0, 0, True, False, False))
        assert farm_view._viewport_x > initial_x
        assert farm_view._viewport_y == initial_y

        farm_view.on_mouse_scroll_up(MouseScrollUp(0, 0, 0, 0, 0, True, False, False))
        assert farm_view._viewport_x == initial_x


async def test_scroll_works_in_edit_mode():
    """Scroll should still pan the viewport even in edit mode."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test() as pilot:
        farm_view = app.query_one("#farm-view", FarmView)
        await pilot.press("e")
        assert farm_view.edit_mode

        initial_y = farm_view._viewport_y
        farm_view.on_mouse_scroll_down(MouseScrollDown(0, 0, 0, 0, 0, 0, False, False, False))
        assert farm_view._viewport_y > initial_y


# ------------------------------------------------------------------
# Hit-testing tests
# ------------------------------------------------------------------


async def test_pig_at_screen_pos_finds_pig():
    """Hit-testing should find a pig at its computed screen position."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test():
        pig = _add_test_pig(app, x=10.0, y=10.0)
        farm_view = app.query_one("#farm-view", FarmView)
        screen_x, screen_y = _pig_screen_center(farm_view, pig)
        found = farm_view._pig_at_screen_pos(screen_x, screen_y)
        assert found is not None
        assert found.id == pig.id


async def test_pig_at_screen_pos_returns_none_for_empty():
    """Hit-testing empty space should return None."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test():
        farm_view = app.query_one("#farm-view", FarmView)
        assert farm_view._pig_at_screen_pos(0, 0) is None


# ------------------------------------------------------------------
# Click tests
# ------------------------------------------------------------------


async def test_click_on_pig_posts_pig_clicked():
    """Clicking a pig's position should find it and post PigClicked."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test():
        pig = _add_test_pig(app, x=10.0, y=10.0)
        farm_view = app.query_one("#farm-view", FarmView)
        screen_x, screen_y = _pig_screen_center(farm_view, pig)

        # Verify the click handler finds the pig and would post PigClicked
        found = farm_view._pig_at_screen_pos(screen_x, screen_y)
        assert found is not None
        assert found.id == pig.id

        # Verify the handler chain: PigClicked → _follow_pig
        screen = app.query_one(MainGameScreen)
        screen._follow_pig(found)
        assert farm_view.selected_pig_id == pig.id


async def test_click_empty_posts_empty_clicked():
    """Clicking empty space should post EmptyClicked and stop following."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test():
        pig = _add_test_pig(app)
        farm_view = app.query_one("#farm-view", FarmView)
        screen = app.query_one(MainGameScreen)
        screen._follow_pig(pig)
        assert farm_view.selected_pig_id == pig.id

        # Verify empty space returns no pig
        assert farm_view._pig_at_screen_pos(0, 0) is None

        # Verify the handler chain: EmptyClicked → _stop_following
        screen._stop_following()
        assert farm_view.selected_pig_id is None


async def test_click_ignored_in_edit_mode():
    """on_click should return early in edit mode without posting messages."""
    app = BigPigFarmApp(debug=False)
    async with app.run_test() as pilot:
        _add_test_pig(app, x=10.0, y=10.0)
        farm_view = app.query_one("#farm-view", FarmView)

        await pilot.press("e")
        assert farm_view.edit_mode

        # Capture any messages posted by on_click
        messages: list = []
        original_post = farm_view.post_message

        def capture_post(msg):
            messages.append(msg)
            return original_post(msg)

        farm_view.post_message = capture_post
        # Click somewhere on the farm — edit mode should block ALL messages
        farm_view.on_click(Click(20, 10, 0, 0, 0, 0, False, False, False))
        farm_view.post_message = original_post

        assert len(messages) == 0
        assert farm_view.selected_pig_id is None
