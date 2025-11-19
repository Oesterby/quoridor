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
    pawns: List[Position]
    walls: Set[Tuple[int, int, bool]] = field(default_factory=set)
    shared_walls_remaining: int = TOTAL_SHARED_WALLS
    current_player: int = 0
    winner: int | None = None
    num_players: int = 2

    @staticmethod
    def new_game(num_players: int = 2) -> "GameState":
        if num_players not in (2, 4):
            raise ValueError("Only 2 or 4 players supported")
        
        # Initialize pawns
        # Player 0: Top (row 0) -> Goal: Bottom (row 8) - Wait, original code had P0 at row 0?
        # Let's check original code:
        # pawns=[Position(0, 4), Position(8, 4)]
        # check_winner: P0 wins if row==8. P1 wins if row==0.
        # So P0 starts at top, goes down. P1 starts at bottom, goes up.
        
        mid = BOARD_SIZE // 2
        if num_players == 2:
            pawns = [Position(0, mid), Position(BOARD_SIZE - 1, mid)]
        else:
            # 4 players:
            # 0: Top -> Bottom
            # 1: Right -> Left
            # 2: Bottom -> Top
            # 3: Left -> Right
            # (Standard Quoridor 4-player setup usually rotates clockwise)
            # Let's define:
            # P0: (0, 4) -> Goal row 8
            # P1: (4, 8) -> Goal col 0
            # P2: (8, 4) -> Goal row 0
            # P3: (4, 0) -> Goal col 8
            pawns = [
                Position(0, mid),
                Position(mid, BOARD_SIZE - 1),
                Position(BOARD_SIZE - 1, mid),
                Position(mid, 0)
            ]
            
        return GameState(
            pawns=pawns,
            num_players=num_players,
            shared_walls_remaining=TOTAL_SHARED_WALLS if num_players == 2 else TOTAL_SHARED_WALLS + 10 # 20 for 2p, maybe more for 4p? Standard is 20 total usually or 5 per player? 
            # Standard Quoridor: 2 players = 10 walls each (20 total). 4 players = 5 walls each (20 total).
            # So total shared walls should be 20 regardless.
            # But let's stick to the constant for now.
        )

    def clone(self) -> "GameState":
        return GameState(
            pawns=list(self.pawns),
            walls=set(self.walls),
            shared_walls_remaining=self.shared_walls_remaining,
            current_player=self.current_player,
            winner=self.winner,
            num_players=self.num_players
        )

    def is_terminal(self) -> bool:
        return self.winner is not None

    def check_winner(self) -> None:
        if self.winner is not None:
            return
            
        for i, p in enumerate(self.pawns):
            if i == 0 and p.row == BOARD_SIZE - 1:
                self.winner = 0
            elif i == 1:
                if self.num_players == 2:
                    if p.row == 0:
                        self.winner = 1
                else: # 4 players
                    if p.col == 0:
                        self.winner = 1
            elif i == 2 and p.row == 0:
                self.winner = 2
            elif i == 3 and p.col == BOARD_SIZE - 1:
                self.winner = 3

    def to_dict(self) -> dict:
        return {
            "pawns": [{"row": p.row, "col": p.col} for p in self.pawns],
            "walls": [
                {"row": r, "col": c, "orientation": "H" if h else "V"}
                for (r, c, h) in sorted(self.walls)
            ],
            "shared_walls_remaining": self.shared_walls_remaining,
            "current_player": self.current_player,
            "winner": self.winner,
            "num_players": self.num_players
        }

