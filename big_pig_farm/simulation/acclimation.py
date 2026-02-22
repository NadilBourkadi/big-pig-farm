"""Biome acclimation — pigs adopt a new preferred biome after extended stays."""

from big_pig_farm.data.config import BIOME, TIME
from big_pig_farm.entities.guinea_pig import GuineaPig

# Pre-compute acclimation threshold in game-hours
_ACCLIMATION_HOURS = BIOME.ACCLIMATION_DAYS * TIME.GAME_HOURS_PER_DAY


def update_acclimation(pig: GuineaPig, current_biome_str: str | None, hours_per_tick: float) -> None:
    """Advance a pig's biome acclimation timer.

    When a pig spends ACCLIMATION_DAYS continuously in a biome that isn't
    its preferred_biome, it adopts the new biome.  The timer resets if the
    pig returns home or moves to a third biome.
    """
    if pig.preferred_biome is None or current_biome_str is None:
        return

    if current_biome_str == pig.preferred_biome:
        # Home biome — reset timer
        pig.acclimation_timer = 0.0
        pig.acclimating_biome = None
        return

    if pig.acclimating_biome != current_biome_str:
        # Changed to a different non-preferred biome — restart timer
        pig.acclimation_timer = 0.0
        pig.acclimating_biome = current_biome_str

    pig.acclimation_timer += hours_per_tick

    if pig.acclimation_timer >= _ACCLIMATION_HOURS:
        pig.preferred_biome = current_biome_str
        pig.acclimation_timer = 0.0
        pig.acclimating_biome = None
