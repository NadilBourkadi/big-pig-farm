"""Tests for Protocol-based facade interfaces."""

from big_pig_farm.game.facades import (
    BirthContext,
    BreedingContext,
    CullingContext,
    NeedsContext,
)
from big_pig_farm.game.state import GameState


def test_game_state_satisfies_needs_context():
    """GameState implements NeedsContext protocol."""
    state = GameState()
    assert isinstance(state, NeedsContext)


def test_game_state_satisfies_breeding_context():
    """GameState implements BreedingContext protocol."""
    state = GameState()
    assert isinstance(state, BreedingContext)


def test_game_state_satisfies_birth_context():
    """GameState implements BirthContext protocol."""
    state = GameState()
    assert isinstance(state, BirthContext)


def test_game_state_satisfies_culling_context():
    """GameState implements CullingContext protocol."""
    state = GameState()
    assert isinstance(state, CullingContext)
