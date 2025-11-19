from __future__ import annotations
import json
import os
from ..engine.state import GameState, Move
from ..engine import rules


class HotseatController:
    """Simple controller abstraction that the renderer can use.
    It delegates legal move queries to the rules module and applies them.
    """

    def __init__(self, state: GameState):
        self.state = state
        self._cached_moves: list[Move] = []
        self.turn: int = (
            0  # increment when player changes (i.e., after a successful move)
        )
        self._last_player: int = state.current_player
        self._players_meta: list[dict] = [
            {"id": 0, "name": "Player 1", "role": "unknown"},
            {"id": 1, "name": "Player 2", "role": "unknown"},
        ]

    def set_player_identities(self, metas: list[dict]) -> None:
        # Expect each meta to have id,name,role
        self._players_meta = metas

    def refresh_moves(self) -> None:
        self._cached_moves = rules.legal_moves(self.state)
        # Detect turn advancement (player switched and game not over)
        if self.state.winner is None and self.state.current_player != self._last_player:
            self.turn += 1
            self._last_player = self.state.current_player
        self._emit_json_snapshot()

    def _emit_json_snapshot(self) -> None:
        """Emit a deterministic JSON snapshot of the current turn state for LLM consumption."""
        # Build wall list
        walls = [
            {"row": r, "col": c, "orientation": "H" if horiz else "V"}
            for (r, c, horiz) in sorted(self.state.walls)
        ]
        # Serialize legal moves with stable IDs
        serialized_moves = []
        # Ensure we have metadata for current player
        if self.state.current_player < len(self._players_meta):
            current_player_name = self._players_meta[self.state.current_player]["name"]
        else:
            current_player_name = f"Player {self.state.current_player + 1}"
            
        current_from_row = self.state.pawns[self.state.current_player].row
        current_from_col = self.state.pawns[self.state.current_player].col
        for idx, m in enumerate(self._cached_moves):
            mid = f"M{idx}"
            if m.kind == "pawn" and m.to:
                serialized_moves.append(
                    {
                        "id": mid,
                        "action": "move_pawn",
                        "piece": current_player_name,
                        "from": {"row": current_from_row, "col": current_from_col},
                        "to": {"row": m.to.row, "col": m.to.col},
                    }
                )
            elif m.kind == "wall" and m.wall:
                serialized_moves.append(
                    {
                        "id": mid,
                        "action": "place_wall",
                        "anchor": {"row": m.wall.row, "col": m.wall.col},
                        "orientation": "H" if m.wall.horizontal else "V",
                    }
                )
        # Build player-centric structures using names (remove P1/P2 abstraction)
        players = []
        for meta in self._players_meta:
            pid = meta["id"]
            # Ensure we don't go out of bounds if state has fewer pawns than meta (shouldn't happen)
            if pid < len(self.state.pawns):
                players.append(
                    {
                        "id": pid,
                        "name": meta["name"],
                        "row": self.state.pawns[pid].row,
                        "col": self.state.pawns[pid].col,
                    }
                )
        
        # Dynamic goal rows/cols based on player count
        goals = []
        board_size = rules.BOARD_SIZE if hasattr(rules, "BOARD_SIZE") else 9
        for i in range(len(self._players_meta)):
            name = self._players_meta[i]["name"]
            if i == 0:
                goals.append({"id": 0, "name": name, "row": board_size - 1})
            elif i == 1:
                if len(self._players_meta) == 2:
                    goals.append({"id": 1, "name": name, "row": 0})
                else:
                    goals.append({"id": 1, "name": name, "col": 0})
            elif i == 2:
                goals.append({"id": 2, "name": name, "row": 0})
            elif i == 3:
                goals.append({"id": 3, "name": name, "col": board_size - 1})

        winner_entry = (
            None
            if self.state.winner is None
            else {
                "id": self.state.winner,
                "name": self._players_meta[self.state.winner]["name"] if self.state.winner < len(self._players_meta) else f"Player {self.state.winner+1}",
            }
        )
        snapshot = {
            "schema": "quoridor.v1",
            "turn": self.turn,
            "current_player": {
                "id": self.state.current_player,
                "name": current_player_name,
            },
            "board": {
                "size": board_size,
                "walls": walls,
            },
            "players": players,
            "shared_walls_remaining": self.state.shared_walls_remaining,
            "goals": goals,
            "winner": winner_entry,
            "legal_moves": serialized_moves,
        }
        if os.getenv("PRINT_SNAPSHOT", "0") == "1":
            print("TURN_STATE_BEGIN")
            print(json.dumps(snapshot, separators=(",", ":")))
            print("TURN_STATE_END")

    @property
    def legal_moves(self) -> list[Move]:
        return self._cached_moves

    def attempt_move(self, move: Move) -> bool:
        # Validate against cached legal moves
        for m in self._cached_moves:
            if move.kind == m.kind and move.to == m.to and move.wall == m.wall:
                self.state = rules.apply_move(self.state, move)
                self.refresh_moves()
                return True
        return False
