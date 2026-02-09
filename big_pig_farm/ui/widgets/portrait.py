"""Reusable pig portrait widget — renders a procedural half-block face."""

from textual.widgets import Static

from big_pig_farm.data.sprite_pixels import (
    generate_portrait,
    convert_pixels,
    render_to_rich_text,
    PALETTES,
)


class PigPortrait(Static):
    """Displays a procedural half-block pig face portrait.

    The portrait reflects all 4 phenotype axes (base color, pattern,
    intensity, roan) and is deterministic per pig UUID.

    Usage::

        portrait = PigPortrait(
            base_color_name="CHOCOLATE",
            pattern="dutch",
            intensity="full",
            roan="none",
            pig_id=str(pig.id),
        )
    """

    DEFAULT_CSS = """
    PigPortrait {
        width: auto;
        height: auto;
    }
    """

    def __init__(
        self,
        base_color_name: str,
        pattern: str,
        intensity: str,
        roan: str,
        pig_id: str,
        **kwargs,
    ):
        portrait_grid = generate_portrait(base_color_name, pattern, intensity, roan, pig_id)
        palette = PALETTES.get(base_color_name, PALETTES["BLACK"])
        converted = convert_pixels(portrait_grid, palette)
        rich_text = render_to_rich_text(converted)
        super().__init__(rich_text, **kwargs)


def portrait_from_pig(pig) -> PigPortrait:
    """Convenience: build a PigPortrait from a GuineaPig entity."""
    return PigPortrait(
        base_color_name=pig.phenotype.base_color.name,
        pattern=pig.phenotype.pattern.value,
        intensity=pig.phenotype.intensity.value,
        roan=pig.phenotype.roan.value,
        pig_id=str(pig.id),
    )
