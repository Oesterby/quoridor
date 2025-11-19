from __future__ import annotations
import random
from .base import GameView
from ...engine.state import Move


class RandomAgent:
    name = "Random Bot"
    is_human = False

    def choose_move(self, view: GameView) -> Move:
        moves = list(view.legal_moves())
        return random.choice(moves)
