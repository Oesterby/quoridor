from __future__ import annotations
from typing import List, Dict, Set, Tuple
from .state import GameState, Position, Move, Wall, BOARD_SIZE

# Adjacency is affected by walls. We model walls as occupying edges between cells.
# Simplified representation: For each cell we test if movement in a direction is blocked by a wall.
# Wall placement validity requires: within bounds, not overlapping/crossing existing walls, and paths remain for both players.

# Directions: up, down, left, right
DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def in_bounds(r: int, c: int) -> bool:
    return 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE


def _build_blocked(state: GameState) -> Dict[Tuple[int, int], Set[Tuple[int, int]]]:
    """Return mapping from cell -> set of blocked direction deltas (dr,dc)."""
    blocked: Dict[Tuple[int, int], Set[Tuple[int, int]]] = {}

    def add_block(a: Tuple[int, int], d: Tuple[int, int]):
        if a not in blocked:
            blocked[a] = set()
        blocked[a].add(d)

    for r, c, horizontal in state.walls:
        if horizontal:
            # blocks vertical movement between rows r and r+1 for columns c and c+1
            for col in (c, c + 1):
                # block (r,col)->(r+1,col) and reverse
                add_block((r, col), (1, 0))
                add_block((r + 1, col), (-1, 0))
        else:
            # vertical wall blocks horizontal movement between cols c and c+1 for rows r and r+1
            for row in (r, r + 1):
                add_block((row, c), (0, 1))
                add_block((row, c + 1), (0, -1))
    return blocked


def _is_blocked(
    blocked: Dict[Tuple[int, int], Set[Tuple[int, int]]],
    r: int,
    c: int,
    dr: int,
    dc: int,
) -> bool:
    return (r, c) in blocked and (dr, dc) in blocked[(r, c)]


def generate_pawn_moves(state: GameState) -> List[Move]:
    blocked = _build_blocked(state)
    moves: List[Move] = []
    me = state.current_player
    other = 1 - me
    my_pos = state.pawns[me]
    opp_pos = state.pawns[other]

    for dr, dc in DIRS:
        nr, nc = my_pos.row + dr, my_pos.col + dc
        if not in_bounds(nr, nc):
            continue
        # edge blocked?
        if _is_blocked(blocked, my_pos.row, my_pos.col, dr, dc):
            continue
        if nr == opp_pos.row and nc == opp_pos.col:
            # opponent adjacent; try straight jump first
            jr, jc = nr + dr, nc + dc
            if in_bounds(jr, jc) and not _is_blocked(
                blocked, opp_pos.row, opp_pos.col, dr, dc
            ):
                # ensure jump edge not blocked from opponent side
                moves.append(Move(kind="pawn", to=Position(jr, jc)))
            else:
                # jump blocked or out of bounds -> try diagonals
                if (
                    dr != 0
                ):  # moving vertically, diagonals left/right relative to opponent
                    diag_options = [(dr, 1), (dr, -1)]
                else:  # moving horizontally, diagonals up/down relative to opponent
                    diag_options = [(1, dc), (-1, dc)]
                for ddr, ddc in diag_options:
                    rr = my_pos.row + ddr
                    cc = my_pos.col + ddc
                    # To reach diagonal, path consists of edge to opponent (already verified not blocked) AND sideways from opponent.
                    # Check bounds and block from opponent position towards diagonal target (difference = (ddr - dr, ddc - dc)?) Simpler: compute opponent->target delta.
                    if not in_bounds(rr, cc):
                        continue
                    # Ensure initial adjacency not blocked (already confirmed) AND sideways from opponent to target not blocked.
                    opp_to_diag_dr = rr - opp_pos.row
                    opp_to_diag_dc = cc - opp_pos.col
                    if _is_blocked(
                        blocked,
                        opp_pos.row,
                        opp_pos.col,
                        opp_to_diag_dr,
                        opp_to_diag_dc,
                    ):
                        continue
                    moves.append(Move(kind="pawn", to=Position(rr, cc)))
        else:
            moves.append(Move(kind="pawn", to=Position(nr, nc)))

    # Deduplicate
    unique: Dict[Tuple[int, int], Move] = {}
    for m in moves:
        if m.to and (m.to.row, m.to.col) not in unique:
            unique[(m.to.row, m.to.col)] = m
    return list(unique.values())


def generate_wall_moves(state: GameState) -> List[Move]:
    """Return only wall placements that preserve at least one path to goal for both players.

    Enforces:
    - No overlapping walls (cannot reuse same blocked edges)
    - No crossing (disallow placing a horizontal and vertical wall with same anchor producing an X)
      (Note: meeting at edges is naturally handled by distinct anchors.)
    - Path continuity: both players must retain at least one path to goal.
    """
    # Shared wall pool gating
    if state.shared_walls_remaining <= 0:
        return []
    moves: List[Move] = []

    # Precompute existing wall anchors by orientation and blocked edges for overlap detection.
    existing_horizontal: Set[Tuple[int, int]] = set()
    existing_vertical: Set[Tuple[int, int]] = set()
    blocked_edges: Set[Tuple[Tuple[int, int], Tuple[int, int]]] = set()

    def wall_edges(
        r: int, c: int, horizontal: bool
    ) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        if horizontal:
            # edges between (r,c)-(r+1,c) and (r,c+1)-(r+1,c+1)
            return [((r, c), (r + 1, c)), ((r, c + 1), (r + 1, c + 1))]
        else:
            # edges between (r,c)-(r,c+1) and (r+1,c)-(r+1,c+1)
            return [((r, c), (r, c + 1)), ((r + 1, c), (r + 1, c + 1))]

    for r, c, horiz in state.walls:
        (existing_horizontal if horiz else existing_vertical).add((r, c))
        for e in wall_edges(r, c, horiz):
            # Normalize edge ordering
            a, b = e
            if a > b:
                a, b = b, a
            blocked_edges.add((a, b))

    for r in range(BOARD_SIZE - 1):
        for c in range(BOARD_SIZE - 1):
            for horizontal in (True, False):
                wall = Wall(r, c, horizontal)
                wkey = wall.key()
                if wkey in state.walls:
                    continue
                # Crossing check: block if opposite orientation already at same anchor
                if horizontal and (r, c) in existing_vertical:
                    continue
                if not horizontal and (r, c) in existing_horizontal:
                    continue
                # Overlap check: candidate edges must be unused
                candidate_edges = []
                for e in wall_edges(r, c, horizontal):
                    a, b = e
                    if a > b:
                        a, b = b, a
                    candidate_edges.append((a, b))
                if any(e in blocked_edges for e in candidate_edges):
                    continue
                # simulate
                temp = state.clone()
                temp.walls.add(wkey)
                blocked = _build_blocked(temp)
                if _both_players_have_path(temp, blocked):
                    moves.append(Move(kind="wall", wall=wall))
    return moves


def legal_moves(state: GameState) -> List[Move]:
    if state.is_terminal():
        return []
    return generate_pawn_moves(state) + generate_wall_moves(state)


def apply_move(state: GameState, move: Move) -> GameState:
    new_state = state.clone()
    if move.kind == "pawn" and move.to:
        new_state.pawns[new_state.current_player] = move.to
    elif move.kind == "wall" and move.wall:
        new_state.walls.add(move.wall.key())
        new_state.shared_walls_remaining -= 1
    new_state.check_winner()
    if not new_state.is_terminal():
        new_state.current_player = 1 - new_state.current_player
    return new_state


def _goal_rows_for(player: int) -> Set[int]:
    return {BOARD_SIZE - 1} if player == 0 else {0}


def _player_has_path(
    state: GameState, blocked: Dict[Tuple[int, int], Set[Tuple[int, int]]], player: int
) -> bool:
    start = state.pawns[player]
    goal_rows = _goal_rows_for(player)
    if start.row in goal_rows:
        return True
    from collections import deque

    visited = [[False] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    q = deque([(start.row, start.col)])
    visited[start.row][start.col] = True
    while q:
        r, c = q.popleft()
        if r in goal_rows:
            return True
        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            if not in_bounds(nr, nc):
                continue
            if _is_blocked(blocked, r, c, dr, dc):
                continue
            if not visited[nr][nc]:
                visited[nr][nc] = True
                q.append((nr, nc))
    return False


def _both_players_have_path(
    state: GameState, blocked: Dict[Tuple[int, int], Set[Tuple[int, int]]]
) -> bool:
    return _player_has_path(state, blocked, 0) and _player_has_path(state, blocked, 1)
