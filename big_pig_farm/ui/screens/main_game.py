"""Main game screen - the primary farm view."""

import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import _Bindings
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.containers import Container, Horizontal
from textual.widgets import Footer

from big_pig_farm.data.config import GameSpeed, SPEED_DISPLAY
from big_pig_farm.entities.facilities import FacilityType
from big_pig_farm.game.state import GameState
from big_pig_farm.economy.currency import add_money, format_currency
from big_pig_farm.economy.shop import get_facility_cost
from big_pig_farm.ui.widgets.status_bar import StatusBar
from big_pig_farm.data.sprites import ZoomLevel
from big_pig_farm.ui.widgets.farm_view import FarmView
from big_pig_farm.ui.widgets.pig_sidebar import PigSidebar
from big_pig_farm.ui.screens.shop import ShopScreen
from big_pig_farm.ui.screens.pig_list import PigListScreen
from big_pig_farm.ui.screens.breeding import BreedingScreen
from big_pig_farm.ui.screens.confirm import ConfirmScreen
from big_pig_farm.ui.screens.almanac import JournalScreen
from big_pig_farm.game.auto_arrange import compute_arrangement, apply_arrangement, clear_pig_navigation


class MainGameScreen(Screen):
    """The main game screen showing the farm view."""

    # Normal mode bindings (default)
    BINDINGS = [
        ("f", "feed", "Feed"),
        ("s", "open_shop", "Shop"),
        ("p", "open_pigs", "Pigs"),
        ("b", "open_breeding", "Breed"),
        ("j", "open_journal", "Journal"),
        ("e", "toggle_edit", "Edit"),
        ("space", "toggle_pause", "Pause"),
        ("plus", "speed_up", "+Spd"),
        ("minus", "slow_down", "-Spd"),
        ("equal", "speed_up", None),
        ("right_square_bracket", "zoom_in", "Zoom+"),
        ("left_square_bracket", "zoom_out", "Zoom-"),
        ("tab", "next_pig", None),
        ("n", "new_game", None),
        ("up", "handle_up", None),
        ("down", "handle_down", None),
        ("left", "handle_left", None),
        ("right", "handle_right", None),
        ("escape", "handle_escape", "Esc"),
        ("d", "dump_debug", None),
        ("q", "quit_game", "Quit"),
    ]

    # Edit mode replaces normal-mode footer with edit-specific bindings
    _EDIT_BINDINGS = [
        ("m", "start_move", "Move"),
        ("r", "remove_facility", "Remove"),
        ("a", "auto_arrange", "Auto"),
        ("delete", "remove_facility", None),
        ("enter", "handle_enter", "Place"),
        ("e", "toggle_edit", "Edit"),
        ("up", "handle_up", None),
        ("down", "handle_down", None),
        ("left", "handle_left", None),
        ("right", "handle_right", None),
        ("escape", "handle_escape", "Esc"),
        ("d", "dump_debug", None),
        ("q", "quit_game", "Quit"),
    ]

    DEFAULT_CSS = """
    MainGameScreen {
        layout: vertical;
    }

    #main-content {
        height: 1fr;
        layout: horizontal;
    }

    #farm-container {
        width: 1fr;
        height: 100%;
        border: solid $primary;
        margin: 0 1;
    }

    """

    def __init__(self, state: GameState, **kwargs):
        super().__init__(**kwargs)
        self.state = state
        self._selected_pig_index = -1

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield StatusBar(id="status-bar")

        with Horizontal(id="main-content"):
            with Container(id="farm-container"):
                yield FarmView(self.state, id="farm-view")

            sidebar = PigSidebar(self.state, id="pig-sidebar")
            sidebar.add_class("hidden")
            yield sidebar

        yield Footer()

    def _refresh_footer(self) -> None:
        """Rebuild bindings based on edit mode and refresh footer."""
        try:
            farm_view = self.query_one("#farm-view", FarmView)
            is_edit = farm_view.edit_mode
        except NoMatches:
            is_edit = False
        bindings = self._EDIT_BINDINGS if is_edit else self.BINDINGS
        self._bindings = _Bindings(bindings)
        try:
            footer = self.query_one(Footer)
            footer._bindings_changed(None)
        except NoMatches:
            pass

    def on_mount(self) -> None:
        """Handle screen mount."""
        self.update_display()
        self.set_interval(0.1, self.update_display)

    def update_display(self) -> None:
        """Update all display elements."""
        farm_view = self.query_one("#farm-view", FarmView)
        status_bar = self.query_one("#status-bar", StatusBar)
        pig_sidebar = self.query_one("#pig-sidebar", PigSidebar)

        # Check if we should follow a pig (set by pig list/detail screens)
        if self.app.pig_to_follow:
            pig = self.app.pig_to_follow
            self.app.pig_to_follow = None  # Clear it
            self._follow_pig(pig)

        # Continuous follow cam — re-center on selected pig every tick
        if farm_view.selected_pig_id:
            pig = self.state.get_guinea_pig(farm_view.selected_pig_id)
            if pig:
                farm_view.center_on_pig(pig)
            else:
                self._stop_following()

        status_bar.update_from_state(self.state)
        farm_view.refresh()
        pig_sidebar.refresh_content()


    def action_toggle_pause(self) -> None:
        """Toggle game pause."""
        self.app.engine.toggle_pause()
        status = "PAUSED" if self.state.is_paused else "RUNNING"
        self.notify(f"Game {status}")

    def action_speed_up(self) -> None:
        """Increase game speed."""
        new_speed = self.app.engine.cycle_speed()
        self.notify(f"Speed: {SPEED_DISPLAY[new_speed]}")

    def action_slow_down(self) -> None:
        """Decrease game speed."""
        speeds = [GameSpeed.NORMAL, GameSpeed.FAST, GameSpeed.FASTER, GameSpeed.FASTEST]
        current = self.state.speed
        if current in speeds:
            idx = speeds.index(current)
            if idx > 0:
                self.state.speed = speeds[idx - 1]
                self.notify(f"Speed: {SPEED_DISPLAY[self.state.speed]}")

    def _stop_following(self) -> None:
        """Stop following the currently selected pig."""
        farm_view = self.query_one("#farm-view", FarmView)
        if farm_view.selected_pig_id:
            farm_view.select_pig(None)
            self._selected_pig_index = -1
            self.query_one("#pig-sidebar", PigSidebar).set_pig(None)

    def _follow_pig(self, pig) -> None:
        """Start following a specific pig."""
        # Find the pig's index in the list
        pigs = self.state.get_pigs_list()
        for i, p in enumerate(pigs):
            if p.id == pig.id:
                self._selected_pig_index = i
                break

        self.query_one("#farm-view", FarmView).select_pig(pig.id)
        self.query_one("#pig-sidebar", PigSidebar).set_pig(pig)
        self.notify(f"Following: {pig.name}")

    def action_zoom_in(self) -> None:
        """Zoom in one level."""
        farm_view = self.query_one("#farm-view", FarmView)
        new = farm_view.cycle_zoom(1)
        labels = {ZoomLevel.FAR: "Far", ZoomLevel.NORMAL: "Normal", ZoomLevel.CLOSE: "Close"}
        self.notify(f"Zoom: {labels[new]}")

    def action_zoom_out(self) -> None:
        """Zoom out one level."""
        farm_view = self.query_one("#farm-view", FarmView)
        new = farm_view.cycle_zoom(-1)
        labels = {ZoomLevel.FAR: "Far", ZoomLevel.NORMAL: "Normal", ZoomLevel.CLOSE: "Close"}
        self.notify(f"Zoom: {labels[new]}")

    def action_feed(self) -> None:
        """Refill all food and water facilities."""
        food_bowls = 0
        water_bottles = 0
        hay_racks = 0

        for facility in self.state.get_facilities_list():
            if facility.facility_type == FacilityType.FOOD_BOWL:
                facility.refill()
                food_bowls += 1
            elif facility.facility_type == FacilityType.WATER_BOTTLE:
                facility.refill()
                water_bottles += 1
            elif facility.facility_type == FacilityType.HAY_RACK:
                facility.refill()
                hay_racks += 1

        parts = []
        if food_bowls:
            parts.append(f"{food_bowls} food")
        if water_bottles:
            parts.append(f"{water_bottles} water")
        if hay_racks:
            parts.append(f"{hay_racks} hay")

        if parts:
            self.notify(f"Refilled: {', '.join(parts)}")
        else:
            self.notify("No facilities to refill", severity="warning")

    def action_next_pig(self) -> None:
        """Select the next guinea pig."""
        pigs = self.state.get_pigs_list()
        if not pigs:
            self.notify("No guinea pigs!", severity="warning")
            return

        self._selected_pig_index = (self._selected_pig_index + 1) % len(pigs)
        pig = pigs[self._selected_pig_index]

        self.query_one("#farm-view", FarmView).select_pig(pig.id)
        self.query_one("#pig-sidebar", PigSidebar).set_pig(pig)
        self.notify(f"Selected: {pig.name}")

    def action_toggle_edit(self) -> None:
        """Toggle facility edit mode."""
        farm_view = self.query_one("#farm-view", FarmView)
        is_edit = farm_view.toggle_edit_mode()
        self.query_one("#status-bar", StatusBar).edit_mode = is_edit
        self._refresh_footer()
        if is_edit:
            self.notify("Edit mode on")
        else:
            self.notify("Edit mode off")

    def action_handle_escape(self) -> None:
        """Handle escape - exit edit mode or deselect."""
        farm_view = self.query_one("#farm-view", FarmView)
        if farm_view.edit_mode:
            if farm_view.moving_facility:
                farm_view.confirm_placement()
                self.notify("Placement cancelled")
            else:
                farm_view.toggle_edit_mode()
                self.query_one("#status-bar", StatusBar).edit_mode = False
                self._refresh_footer()
                self.notify("Edit mode off")
        else:
            self._selected_pig_index = -1
            farm_view.select_pig(None)
            self.query_one("#pig-sidebar", PigSidebar).set_pig(None)

    def action_handle_up(self) -> None:
        """Handle up arrow."""
        farm_view = self.query_one("#farm-view", FarmView)
        if farm_view.edit_mode:
            farm_view.move_cursor(0, -1)
        else:
            self._stop_following()
            farm_view.scroll(0, -2)

    def action_handle_down(self) -> None:
        """Handle down arrow."""
        farm_view = self.query_one("#farm-view", FarmView)
        if farm_view.edit_mode:
            farm_view.move_cursor(0, 1)
        else:
            self._stop_following()
            farm_view.scroll(0, 2)

    def action_handle_left(self) -> None:
        """Handle left arrow."""
        farm_view = self.query_one("#farm-view", FarmView)
        if farm_view.edit_mode:
            farm_view.move_cursor(-1, 0)
        else:
            self._stop_following()
            farm_view.scroll(-2, 0)

    def action_handle_right(self) -> None:
        """Handle right arrow."""
        farm_view = self.query_one("#farm-view", FarmView)
        if farm_view.edit_mode:
            farm_view.move_cursor(1, 0)
        else:
            self._stop_following()
            farm_view.scroll(2, 0)

    def action_handle_enter(self) -> None:
        """Handle enter key."""
        farm_view = self.query_one("#farm-view", FarmView)
        if not farm_view.edit_mode:
            return

        if farm_view.moving_facility:
            farm_view.confirm_placement()
            self.notify("Facility placed!", severity="information")
        else:
            facility = farm_view.select_facility_at_cursor()
            if facility:
                name = facility.facility_type.display_name
                self.notify(f"Selected: {name} (M to move, R to remove)")
            else:
                self.notify("No facility here", severity="warning")

    def action_start_move(self) -> None:
        """Start moving selected facility."""
        farm_view = self.query_one("#farm-view", FarmView)
        if farm_view.edit_mode:
            if farm_view.start_moving_facility():
                self.notify("Moving facility - arrows to move, Enter to place")
            else:
                self.notify("Select a facility first (Enter)", severity="warning")

    def action_remove_facility(self) -> None:
        """Remove the selected facility and refund its cost."""
        farm_view = self.query_one("#farm-view", FarmView)
        if farm_view.edit_mode:
            facility = farm_view.get_selected_facility()
            if facility:
                refund = get_facility_cost(facility.facility_type)
                farm_view.remove_selected_facility()
                add_money(self.state, refund, f"Removed {facility.facility_type.display_name}")
                name = facility.facility_type.display_name
                self.notify(f"Removed: {name} (+{format_currency(refund)})", severity="information")
            else:
                self.notify("Select a facility first (Enter)", severity="warning")

    def action_auto_arrange(self) -> None:
        """Auto-arrange all facilities into logical zones."""
        farm_view = self.query_one("#farm-view", FarmView)
        if not farm_view.edit_mode:
            return

        if not self.state.get_facilities_list():
            self.notify("No facilities to arrange")
            return

        def handle_confirm(confirmed: bool) -> None:
            if not confirmed:
                return
            placements, overflow = compute_arrangement(self.state)
            apply_arrangement(self.state, placements, overflow)
            clear_pig_navigation(self.state)
            self.app.behavior_controller.reset_all_tracking()

            placed_count = len(placements)
            if overflow:
                self.notify(
                    f"Arranged {placed_count} facilities "
                    f"({len(overflow)} couldn't fit)",
                    severity="warning",
                )
            else:
                self.notify(f"Arranged {placed_count} facilities into zones")

        self.app.push_screen(
            ConfirmScreen(
                "Auto-arrange all facilities?\n"
                "Positions will be reorganized into zones."
            ),
            handle_confirm,
        )

    def action_open_shop(self) -> None:
        """Open the shop screen."""
        self.app.push_screen(ShopScreen(self.state))

    def action_open_pigs(self) -> None:
        """Open the pig list screen."""
        self.app.push_screen(PigListScreen(self.state))

    def action_open_breeding(self) -> None:
        """Open the breeding screen."""
        self.app.push_screen(BreedingScreen(self.state))

    def action_open_journal(self) -> None:
        """Open the journal (Pigdex, Contracts, Event Log)."""
        self.app.push_screen(JournalScreen(self.state))

    def action_new_game(self) -> None:
        """Start a new game (with confirmation)."""
        def handle_confirm(confirmed: bool) -> None:
            if confirmed:
                # Delete save and restart
                self.app.save_manager.delete_save()
                self.notify("Starting new game...")
                self.app.exit()

        self.app.push_screen(
            ConfirmScreen("Start a new game?\nAll progress will be lost!"),
            handle_confirm
        )

    def action_dump_debug(self) -> None:
        """Dump full debug state for all pigs and facilities to a file."""
        controller = self.app.behavior_controller
        lines = []
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"=== DEBUG DUMP {now} ===")
        lines.append(f"Speed: {SPEED_DISPLAY[self.state.speed]}  Paused: {self.state.is_paused}")
        lines.append(f"Money: ${self.state.money}  Pigs: {len(self.state.get_pigs_list())}  Facilities: {len(self.state.get_facilities_list())}")
        lines.append("")

        # Facilities
        lines.append("--- FACILITIES ---")
        for f in self.state.get_facilities_list():
            lines.append(f"  {f.name} [{f.id.hex[:8]}] at ({f.position_x},{f.position_y}) size={f.width}x{f.height}")
            lines.append(f"    amount={f.current_amount:.1f}/{f.max_amount:.1f} empty={f.is_empty}")
            lines.append(f"    interaction_point={f.interaction_point}  all_points={f.interaction_points}")
        lines.append("")

        # Pigs
        lines.append("--- PIGS ---")
        for pig in self.state.get_pigs_list():
            decision_timer = controller._decision_timers.get(pig.id, 0)
            blocked_timer = controller._blocked_timers.get(pig.id, 0)
            failed = controller.facility_manager.get_failed_facilities(pig.id)
            failed_names = []
            for fid in failed:
                fac = self.state.get_facility(fid)
                failed_names.append(f"{fac.name}[{fid.hex[:8]}]" if fac else f"[{fid.hex[:8]}]")

            lines.append(f"  {pig.name} [{pig.id.hex[:8]}]")
            lines.append(f"    state={pig.behavior_state.value}  pos=({pig.position.x:.1f},{pig.position.y:.1f})  grid={pig.position.grid_pos()}")
            lines.append(f"    target_desc={pig.target_description}")
            lines.append(f"    target_pos={f'({pig.target_position.x:.1f},{pig.target_position.y:.1f})' if pig.target_position else 'None'}")
            lines.append(f"    target_facility={pig.target_facility_id.hex[:8] if pig.target_facility_id else 'None'}")
            lines.append(f"    path_len={len(pig.path)}  path_next={pig.path[0] if pig.path else 'None'}")
            lines.append(f"    needs: hunger={pig.needs.hunger:.1f} thirst={pig.needs.thirst:.1f} energy={pig.needs.energy:.1f} happiness={pig.needs.happiness:.1f} social={pig.needs.social:.1f} boredom={pig.needs.boredom:.1f} health={pig.needs.health:.1f}")
            lines.append(f"    timers: decision={decision_timer:.2f}s  blocked={blocked_timer:.2f}s")
            lines.append(f"    failed_facilities: {', '.join(failed_names) if failed_names else 'none'}")
            lines.append(f"    personality: {[p.value for p in pig.personality]}")
            lines.append(f"    behavior_log (last 10):")
            for entry in pig.behavior_log[-10:]:
                lines.append(f"      - {entry}")
            lines.append("")

        dump_dir = Path.home() / ".big_pig_farm"
        dump_dir.mkdir(exist_ok=True)
        dump_path = dump_dir / "debug_dump.txt"
        dump_path.write_text("\n".join(lines))
        self.notify(f"Debug dump saved to {dump_path}")

    def action_quit_game(self) -> None:
        """Quit the game."""
        self.app.exit()
