from __future__ import annotations
from typing import List, Dict, Set, Tuple, Callable
from .state import GameState, Position, Move, Wall, BOARD_SIZE

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
    my_pos = state.pawns[me]
    
    # Identify positions of all other pawns
    other_positions = {
        (p.row, p.col) 
        for i, p in enumerate(state.pawns) 
        if i != me
    }

    for dr, dc in DIRS:
        nr, nc = my_pos.row + dr, my_pos.col + dc
        if not in_bounds(nr, nc):
            continue
        
        # edge blocked?
        if _is_blocked(blocked, my_pos.row, my_pos.col, dr, dc):
            continue
            
        if (nr, nc) in other_positions:
            # opponent adjacent; try straight jump first
            jr, jc = nr + dr, nc + dc
            
            # Check if jump is blocked by wall OR by another pawn
            jump_blocked_by_wall = _is_blocked(blocked, nr, nc, dr, dc)
            jump_blocked_by_pawn = (jr, jc) in other_positions
            
            if in_bounds(jr, jc) and not jump_blocked_by_wall and not jump_blocked_by_pawn:
                moves.append(Move(kind="pawn", to=Position(jr, jc)))
            else:
                # jump blocked or out of bounds -> try diagonals
                # Diagonals are relative to the opponent we are facing
                if dr != 0:  # moving vertically
                    diag_options = [(dr, 1), (dr, -1)] # (1,1), (1,-1) or (-1,1), (-1,-1) relative to my_pos? No.
                    # If I move (1,0) to opp, diag is (1,1) and (1,-1) from ME.
                    # Which is (0,1) and (0,-1) from OPP.
                    # Let's use the logic: from OPP, move perpendicular to original direction
                    ortho_dirs = [(0, 1), (0, -1)]
                else:  # moving horizontally
                    ortho_dirs = [(1, 0), (-1, 0)]
                
                for odr, odc in ortho_dirs:
                    # Target is opponent pos + ortho dir
                    tr, tc = nr + odr, nc + odc
                    
                    if not in_bounds(tr, tc):
                        continue
                        
                    # Check if path from opponent to target is blocked by wall
                    if _is_blocked(blocked, nr, nc, odr, odc):
                        continue
                        
                    # Check if target is occupied by another pawn
                    if (tr, tc) in other_positions:
                        continue
                        
                    moves.append(Move(kind="pawn", to=Position(tr, tc)))
        else:
            moves.append(Move(kind="pawn", to=Position(nr, nc)))

    # Deduplicate
    unique: Dict[Tuple[int, int], Move] = {}
    for m in moves:
        if m.to and (m.to.row, m.to.col) not in unique:
            unique[(m.to.row, m.to.col)] = m
    return list(unique.values())


def generate_wall_moves(state: GameState) -> List[Move]:
    """Return only wall placements that preserve at least one path to goal for ALL players."""
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
            return [((r, c), (r + 1, c)), ((r, c + 1), (r + 1, c + 1))]
        else:
            return [((r, c), (r, c + 1)), ((r + 1, c), (r + 1, c + 1))]

    for r, c, horiz in state.walls:
        (existing_horizontal if horiz else existing_vertical).add((r, c))
        for e in wall_edges(r, c, horiz):
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
                # Crossing check
                if horizontal and (r, c) in existing_vertical:
                    continue
                if not horizontal and (r, c) in existing_horizontal:
                    continue
                # Overlap check
                candidate_edges = []
                for e in wall_edges(r, c, horizontal):
                    a, b = e
                    if a > b:
                        a, b = b, a
                    candidate_edges.append((a, b))
                if any(e in blocked_edges for e in candidate_edges):
                    continue
                
                # simulate
                # Optimization: Check path validity only if it blocks a critical path?
                # For now, just simulate.
                temp = state.clone()
                temp.walls.add(wkey)
                blocked = _build_blocked(temp)
                if _all_players_have_path(temp, blocked):
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
        new_state.current_player = (new_state.current_player + 1) % new_state.num_players
    return new_state


def _get_goal_check(player: int, num_players: int) -> Callable[[int, int], bool]:
    if player == 0:
        return lambda r, c: r == BOARD_SIZE - 1
    elif player == 1:
        if num_players == 2:
            return lambda r, c: r == 0
        else:
            return lambda r, c: c == 0
    elif player == 2:
        return lambda r, c: r == 0
    elif player == 3:
        return lambda r, c: c == BOARD_SIZE - 1
    return lambda r, c: False


def _player_has_path(
    state: GameState, blocked: Dict[Tuple[int, int], Set[Tuple[int, int]]], player: int
) -> bool:
    start = state.pawns[player]
    is_goal = _get_goal_check(player, state.num_players)
    
    if is_goal(start.row, start.col):
        return True
        
    from collections import deque

    visited = [[False] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    q = deque([(start.row, start.col)])
    visited[start.row][start.col] = True
    
    while q:
        r, c = q.popleft()
        if is_goal(r, c):
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


def _all_players_have_path(
    state: GameState, blocked: Dict[Tuple[int, int], Set[Tuple[int, int]]]
) -> bool:
    for p in range(state.num_players):
        if not _player_has_path(state, blocked, p):
            return False
    return True

