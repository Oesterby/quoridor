from __future__ import annotations
from typing import Protocol, Iterable
from ...engine.state import GameState, Move
from ...engine import rules


class GameView:
    """Read-only adapter given to agents."""

    def __init__(self, state: GameState):
        self._state = state
        self._legal = rules.legal_moves(state)

    @property
    def state(self) -> GameState:
        return self._state

    def current_player(self) -> int:
        return self._state.current_player

    def legal_moves(self) -> Iterable[Move]:
        return self._legal


class Agent(Protocol):
    name: str
    is_human: bool

    def choose_move(self, view: GameView) -> Move: ...
