"""Main game screen - the primary farm view."""

import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal
from textual.widgets import Footer

from big_pig_farm.data.config import GameSpeed, SPEED_DISPLAY
from big_pig_farm.entities.facilities import FacilityType
from big_pig_farm.game.state import GameState
from big_pig_farm.economy.currency import add_money
from big_pig_farm.economy.shop import get_facility_cost
from big_pig_farm.ui.widgets.status_bar import StatusBar
from big_pig_farm.ui.widgets.farm_view import FarmView
from big_pig_farm.ui.widgets.notification import NotificationBar
from big_pig_farm.ui.widgets.pig_sidebar import PigSidebar
from big_pig_farm.ui.screens.shop import ShopScreen
from big_pig_farm.ui.screens.pig_list import PigListScreen
from big_pig_farm.ui.screens.breeding import BreedingScreen
from big_pig_farm.ui.screens.facilities import FacilitiesScreen
from big_pig_farm.ui.screens.confirm import ConfirmScreen
from big_pig_farm.ui.screens.adoption import AdoptionScreen
from big_pig_farm.ui.screens.almanac import AlmanacScreen


class MainGameScreen(Screen):
    """The main game screen showing the farm view."""

    BINDINGS = [
        # Normal mode bindings (hidden in edit mode via check_action)
        ("f", "feed", "Feed"),
        ("s", "open_shop", "Shop"),
        ("a", "open_adoption", "Adopt"),
        ("p", "open_pigs", "Pigs"),
        ("b", "open_breeding", "Breed"),
        ("j", "open_almanac", "Almanac"),
        ("e", "toggle_edit", "Edit"),
        ("space", "toggle_pause", "Pause"),
        ("plus", "speed_up", "+Spd"),
        ("minus", "slow_down", "-Spd"),
        ("equal", "speed_up", None),
        ("tab", "next_pig", None),
        ("n", "new_game", None),
        # Edit mode bindings (shown only in edit mode via check_action)
        ("m", "start_move", "Move"),
        ("r", "remove_facility", "Remove"),
        ("delete", "remove_facility", None),
        ("enter", "handle_enter", "Place"),
        # Always available (hidden from footer)
        ("up", "handle_up", None),
        ("down", "handle_down", None),
        ("left", "handle_left", None),
        ("right", "handle_right", None),
        ("escape", "handle_escape", "Esc"),
        ("d", "dump_debug", None),
        ("q", "quit_game", "Quit"),
    ]

    # Actions that should only appear in the footer when in edit mode
    _EDIT_ONLY_ACTIONS = {"start_move", "remove_facility", "handle_enter"}
    # Actions that should only appear in the footer when NOT in edit mode
    _NORMAL_ONLY_ACTIONS = {
        "feed", "open_shop", "open_adoption", "open_pigs",
        "open_breeding", "open_almanac", "toggle_pause",
        "speed_up", "slow_down", "next_pig", "new_game",
    }

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        """Control which bindings appear in footer based on edit mode."""
        is_edit = self._farm_view and self._farm_view.edit_mode
        if action in self._EDIT_ONLY_ACTIONS and not is_edit:
            return False
        if action in self._NORMAL_ONLY_ACTIONS and is_edit:
            return False
        return True

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

    #notification-container {
        height: 1;
        margin: 0 1;
    }
    """

    def __init__(self, state: GameState, **kwargs):
        super().__init__(**kwargs)
        self.state = state
        self._status_bar: StatusBar | None = None
        self._farm_view: FarmView | None = None
        self._notification_bar: NotificationBar | None = None
        self._pig_sidebar: PigSidebar | None = None
        self._selected_pig_index = -1

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        self._status_bar = StatusBar()
        yield self._status_bar

        with Horizontal(id="main-content"):
            with Container(id="farm-container"):
                self._farm_view = FarmView(self.state)
                yield self._farm_view

            self._pig_sidebar = PigSidebar(self.state)
            self._pig_sidebar.add_class("hidden")
            yield self._pig_sidebar

        with Container(id="notification-container"):
            self._notification_bar = NotificationBar()
            yield self._notification_bar

        yield Footer()

    def _refresh_footer(self) -> None:
        """Refresh the footer to update visible bindings."""
        try:
            footer = self.query_one(Footer)
            footer.refresh()
        except Exception:
            pass

    def on_mount(self) -> None:
        """Handle screen mount."""
        self.update_display()
        self.set_interval(0.1, self.update_display)

    def update_display(self) -> None:
        """Update all display elements."""
        # Check if we should follow a pig (set by pig list/detail screens)
        if self.app.pig_to_follow:
            pig = self.app.pig_to_follow
            self.app.pig_to_follow = None  # Clear it
            self._follow_pig(pig)

        if self._status_bar:
            self._status_bar.update_from_state(self.state)

        if self._farm_view:
            self._farm_view.refresh()

        if self._pig_sidebar:
            self._pig_sidebar.refresh_content()

        if self._notification_bar and self.state.events:
            last_event = self.state.events[-1]
            if not self._notification_bar.messages or \
               self._notification_bar.messages[-1] != f"🔔 {last_event.message}":
                self._notification_bar.add_message(
                    last_event.message,
                    last_event.event_type,
                )

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

    def _follow_pig(self, pig) -> None:
        """Start following a specific pig."""
        # Find the pig's index in the list
        pigs = self.state.get_pigs_list()
        for i, p in enumerate(pigs):
            if p.id == pig.id:
                self._selected_pig_index = i
                break

        if self._farm_view:
            self._farm_view.select_pig(pig.id)
        if self._pig_sidebar:
            self._pig_sidebar.set_pig(pig)
        self.notify(f"Following: {pig.name}")

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
            self.notify("No facilities to refill")

    def action_next_pig(self) -> None:
        """Select the next guinea pig."""
        pigs = self.state.get_pigs_list()
        if not pigs:
            self.notify("No guinea pigs!")
            return

        self._selected_pig_index = (self._selected_pig_index + 1) % len(pigs)
        pig = pigs[self._selected_pig_index]

        if self._farm_view:
            self._farm_view.select_pig(pig.id)
        if self._pig_sidebar:
            self._pig_sidebar.set_pig(pig)
        self.notify(f"Selected: {pig.name}")

    def action_toggle_edit(self) -> None:
        """Toggle facility edit mode."""
        if self._farm_view:
            is_edit = self._farm_view.toggle_edit_mode()
            if self._status_bar:
                self._status_bar.edit_mode = is_edit
            self._refresh_footer()
            if is_edit:
                self.notify("EDIT MODE: Arrows move cursor, Enter selects, M moves, R removes, Esc exits")
            else:
                self.notify("Edit mode off")

    def action_handle_escape(self) -> None:
        """Handle escape - exit edit mode or deselect."""
        if self._farm_view and self._farm_view.edit_mode:
            if self._farm_view.moving_facility:
                self._farm_view.confirm_placement()
                self.notify("Placement cancelled")
            else:
                self._farm_view.toggle_edit_mode()
                if self._status_bar:
                    self._status_bar.edit_mode = False
                self._refresh_footer()
                self.notify("Edit mode off")
        else:
            self._selected_pig_index = -1
            if self._farm_view:
                self._farm_view.select_pig(None)
            if self._pig_sidebar:
                self._pig_sidebar.set_pig(None)

    def action_handle_up(self) -> None:
        """Handle up arrow."""
        if self._farm_view:
            if self._farm_view.edit_mode:
                self._farm_view.move_cursor(0, -1)
            else:
                self._farm_view.scroll(0, -2)

    def action_handle_down(self) -> None:
        """Handle down arrow."""
        if self._farm_view:
            if self._farm_view.edit_mode:
                self._farm_view.move_cursor(0, 1)
            else:
                self._farm_view.scroll(0, 2)

    def action_handle_left(self) -> None:
        """Handle left arrow."""
        if self._farm_view:
            if self._farm_view.edit_mode:
                self._farm_view.move_cursor(-1, 0)
            else:
                self._farm_view.scroll(-2, 0)

    def action_handle_right(self) -> None:
        """Handle right arrow."""
        if self._farm_view:
            if self._farm_view.edit_mode:
                self._farm_view.move_cursor(1, 0)
            else:
                self._farm_view.scroll(2, 0)

    def action_handle_enter(self) -> None:
        """Handle enter key."""
        if not self._farm_view or not self._farm_view.edit_mode:
            return

        if self._farm_view.moving_facility:
            self._farm_view.confirm_placement()
            self.notify("Facility placed!")
        else:
            facility = self._farm_view.select_facility_at_cursor()
            if facility:
                name = facility.facility_type.display_name
                self.notify(f"Selected: {name} (M to move, R to remove)")
            else:
                self.notify("No facility here")

    def action_start_move(self) -> None:
        """Start moving selected facility."""
        if self._farm_view and self._farm_view.edit_mode:
            if self._farm_view.start_moving_facility():
                self.notify("Moving facility - arrows to move, Enter to place")
            else:
                self.notify("Select a facility first (Enter)")

    def action_remove_facility(self) -> None:
        """Remove the selected facility and refund its cost."""
        if self._farm_view and self._farm_view.edit_mode:
            facility = self._farm_view.get_selected_facility()
            if facility:
                # Get refund amount before removing
                refund = get_facility_cost(facility.facility_type)
                # Remove the facility
                self._farm_view.remove_selected_facility()
                # Add refund
                add_money(self.state, refund, f"Removed {facility.facility_type.display_name}")
                name = facility.facility_type.display_name
                self.notify(f"Removed: {name} (+${refund})")
            else:
                self.notify("Select a facility first (Enter)")

    def action_open_shop(self) -> None:
        """Open the shop screen."""
        self.app.push_screen(ShopScreen(self.state))

    def action_open_adoption(self) -> None:
        """Open the adoption center screen."""
        self.app.push_screen(AdoptionScreen(self.state))

    def action_open_pigs(self) -> None:
        """Open the pig list screen."""
        self.app.push_screen(PigListScreen(self.state))

    def action_open_breeding(self) -> None:
        """Open the breeding screen."""
        self.app.push_screen(BreedingScreen(self.state))

    def action_open_almanac(self) -> None:
        """Open the almanac (Pigdex, Contracts, Event Log)."""
        self.app.push_screen(AlmanacScreen(self.state))

    def action_open_facilities(self) -> None:
        """Open the facilities screen."""
        self.app.push_screen(FacilitiesScreen(self.state))

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
            failed = controller._failed_facilities.get(pig.id, set())
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
