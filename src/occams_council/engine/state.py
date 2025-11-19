from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Set, Tuple

BOARD_SIZE = 9
MAX_WALLS_PER_PLAYER = 10  # legacy per-player count (10 each => 20 total)
TOTAL_SHARED_WALLS = MAX_WALLS_PER_PLAYER * 2


@dataclass(frozen=True)
class Position:
    row: int
    col: int

    def in_bounds(self) -> bool:
        return 0 <= self.row < BOARD_SIZE and 0 <= self.col < BOARD_SIZE


@dataclass(frozen=True)
class Wall:
    row: int  # top-left cell (anchor) of wall segment intersection
    col: int
    horizontal: bool  # True => spans horizontally between columns, blocks vertical movement below/above

    def key(self) -> Tuple[int, int, bool]:
        return (self.row, self.col, self.horizontal)


@dataclass(frozen=True)
class Move:
    kind: str  # 'pawn' or 'wall'
    to: Position | None = None
    wall: Wall | None = None


@dataclass
class GameState:
    pawns: List[Position] = field(
        default_factory=lambda: [
            Position(0, BOARD_SIZE // 2),
            Position(BOARD_SIZE - 1, BOARD_SIZE // 2),
        ]
    )
    walls: Set[Tuple[int, int, bool]] = field(default_factory=set)
    # Shared pool of walls remaining for the entire game (instead of per-player counts)
    shared_walls_remaining: int = TOTAL_SHARED_WALLS
    current_player: int = 0
    winner: int | None = None

    def clone(self) -> "GameState":
        return GameState(
            pawns=list(self.pawns),
            walls=set(self.walls),
            shared_walls_remaining=self.shared_walls_remaining,
            current_player=self.current_player,
            winner=self.winner,
        )

    def is_terminal(self) -> bool:
        if self.pawns[0].row == BOARD_SIZE - 1:
            return True
        if self.pawns[1].row == 0:
            return True
        return False

    def check_winner(self) -> None:
        if self.pawns[0].row == BOARD_SIZE - 1:
            self.winner = 0
        elif self.pawns[1].row == 0:
            self.winner = 1
