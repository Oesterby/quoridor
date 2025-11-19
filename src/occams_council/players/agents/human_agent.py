from __future__ import annotations
from typing import Optional
from .base import GameView
from ...engine.state import Move


class HumanAgent:
    is_human = True

    def __init__(self, name: str = "Human"):
        self.name = name
        self.pending_move: Optional[Move] = None

    def set_pending(self, move: Move):
        self.pending_move = move

    def choose_move(self, view: GameView) -> Move:
        assert self.pending_move is not None, "Human move requested but none is pending"
        mv = self.pending_move
        self.pending_move = None
        return mv
