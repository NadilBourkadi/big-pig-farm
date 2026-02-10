"""Offline progression calculator."""

from datetime import datetime
from typing import Any

from big_pig_farm.data.config import TIME, NEEDS
from big_pig_farm.entities.facilities import FacilityType
from big_pig_farm.game.state import GameState
from big_pig_farm.simulation.needs import update_all_needs
from big_pig_farm.simulation.breeding import (
    advance_pregnancies,
    age_all_pigs,
    check_breeding_opportunities,
)


def calculate_offline_progress(state: GameState) -> dict[str, Any]:
    """Calculate what happened while the game was closed.

    Returns a summary dict of events that occurred.
    """
    now = datetime.now()
    last_update = state.game_time.last_update
    elapsed_seconds = (now - last_update).total_seconds()

    # Cap at maximum offline time
    max_offline_seconds = TIME.MAX_OFFLINE_HOURS * 3600
    elapsed_seconds = min(elapsed_seconds, max_offline_seconds)

    if elapsed_seconds < 60:  # Less than a minute, no offline progress
        return {"skipped": True, "reason": "Too short", "elapsed_seconds": elapsed_seconds}

    # Convert to game time (at 1x speed: 1 real second = 1 game minute)
    # But for offline, we simulate faster
    real_hours = elapsed_seconds / 3600
    game_hours = real_hours * 60  # Each real hour = 60 game hours offline

    summary: dict[str, Any] = {
        "real_hours": real_hours,
        "game_hours": game_hours,
        "game_days": game_hours / 24,
        "events": [],
        "births": 0,
        "deaths": 0,
        "income": 0,
        "starting_pigs": state.pig_count,
        "starting_money": state.money,
    }

    # Simulate in chunks (each chunk = 1 game hour)
    hours_to_simulate = int(game_hours)
    hours_to_simulate = min(hours_to_simulate, 24 * 7)  # Cap at 1 week game time

    for _ in range(hours_to_simulate):
        _simulate_offline_hour(state, summary)

    # Update final stats
    summary["ending_pigs"] = state.pig_count
    summary["ending_money"] = state.money
    summary["net_pigs"] = summary["ending_pigs"] - summary["starting_pigs"]
    summary["net_money"] = summary["ending_money"] - summary["starting_money"]

    # Update game time
    state.game_time.advance(game_hours * 60)
    state.game_time.last_update = now

    return summary


def _simulate_offline_hour(state: GameState, summary: dict[str, Any]) -> None:
    """Simulate one hour of offline progression."""
    # Update needs for all pigs (60 game minutes per hour)
    for pig in state.get_pigs_list():
        update_all_needs(pig, 60.0, state)

        # Simple auto-feeding if facilities exist
        _auto_use_facilities(pig, state)

    # Advance pregnancies
    advance_pregnancies(state, 1.0)  # 1 game hour

    # Check for births
    initial_count = state.pig_count
    check_breeding_opportunities(state)
    births = state.pig_count - initial_count
    if births > 0:
        summary["births"] += births
        summary["events"].append(f"{births} guinea pig(s) were born!")

    # Age pigs and check for deaths
    deaths = age_all_pigs(state, 1.0)
    if deaths:
        summary["deaths"] += len(deaths)
        for pig in deaths:
            summary["events"].append(f"{pig.name} passed away.")

    # Advance game time
    state.game_time.advance(60)


def _auto_use_facilities(pig, state: GameState) -> None:
    """Automatically use facilities to satisfy needs during offline."""
    # Auto-eat if hungry and food available
    if pig.needs.hunger < NEEDS.LOW_THRESHOLD:
        food_bowls = state.get_facilities_by_type(FacilityType.FOOD_BOWL)
        for bowl in food_bowls:
            if not bowl.is_empty:
                consumed = bowl.consume(10)
                pig.needs.hunger += consumed * 2
                break

    # Auto-drink if thirsty and water available
    if pig.needs.thirst < NEEDS.LOW_THRESHOLD:
        bottles = state.get_facilities_by_type(FacilityType.WATER_BOTTLE)
        for bottle in bottles:
            if not bottle.is_empty:
                consumed = bottle.consume(10)
                pig.needs.thirst += consumed * 2
                break

    # Auto-sleep if tired (instant recovery for offline)
    if pig.needs.energy < NEEDS.LOW_THRESHOLD:
        pig.needs.energy += NEEDS.OFFLINE_ENERGY_RECOVERY

    # Auto-play if bored and play facility exists
    play_types = [FacilityType.PLAY_AREA, FacilityType.EXERCISE_WHEEL, FacilityType.TUNNEL]
    has_play = any(state.get_facilities_by_type(ft) for ft in play_types)
    if has_play and pig.needs.boredom > NEEDS.LOW_THRESHOLD:
        pig.needs.boredom -= NEEDS.OFFLINE_PLAY_BOREDOM_RECOVERY
        pig.needs.happiness += NEEDS.OFFLINE_PLAY_HAPPINESS_RECOVERY

    # Auto-socialize if other pigs exist
    pig_count = len(state.get_pigs_list())
    if pig_count > 1 and pig.needs.social < NEEDS.LOW_THRESHOLD:
        pig.needs.social += NEEDS.OFFLINE_SOCIAL_RECOVERY
        pig.needs.happiness += NEEDS.OFFLINE_SOCIAL_HAPPINESS_RECOVERY

    pig.needs.clamp_all()


def format_offline_summary(summary: dict[str, Any]) -> str:
    """Format the offline summary for display."""
    if summary.get("skipped"):
        return ""

    lines = [
        "🌙 While you were away...",
        "",
        f"Time passed: {summary['real_hours']:.1f} real hours ({summary['game_days']:.1f} game days)",
        "",
    ]

    if summary["births"] > 0:
        lines.append(f"🎉 {summary['births']} guinea pig(s) were born!")

    if summary["deaths"] > 0:
        lines.append(f"💔 {summary['deaths']} guinea pig(s) passed away.")

    if summary["net_money"] != 0:
        sign = "+" if summary["net_money"] > 0 else ""
        lines.append(f"💰 Money: {sign}{summary['net_money']} Squeaks")

    lines.append("")
    lines.append(f"🐹 You now have {summary['ending_pigs']} guinea pigs")

    if summary["events"]:
        lines.append("")
        lines.append("Recent events:")
        for event in summary["events"][-5:]:  # Last 5 events
            lines.append(f"  • {event}")

    return "\n".join(lines)
