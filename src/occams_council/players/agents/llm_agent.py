from __future__ import annotations
import os
import json
import random
from typing import List, Optional, Any
from .base import GameView
from ...engine.state import Move

SYSTEM_PROMPT = (
    "You are an expert Quoridor player. You must choose a single legal move "
    "that maximizes strategic advantage. Respond ONLY with a compact JSON object: "
    '{\n  "rationale": "Short explanation of strategy",\n  "move_id": "Mx"\n}. '
    "Do not add commentary."
)

class LLMAgent:
    name = "LLM Bot"
    is_human = False

    def __init__(self, model: str | None = None, max_attempts: int = 3):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5.1")
        self.max_attempts = max_attempts
        self.last_raw_response: str | None = None
        self._client: Any = None
        self._init_error: Optional[str] = None
        self._ensure_client()

    def _ensure_client(self) -> None:
        if self._client is not None or self._init_error is not None:
            return
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                self._init_error = "missing_api_key"
                return
            self._client = OpenAI(api_key=api_key)
        except Exception as e:
            self._init_error = f"init_exception:{e}"

    def _call_llm(self, user_prompt: str) -> str | None:
        if self._client is None:
            if self._init_error:
                print(f"LLM_DIAG no_client reason={self._init_error}")
            return None
            
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            content = resp.choices[0].message.content.strip()
            self.last_raw_response = content
            return content
        except Exception as e:
            err = f"ERROR: {e}"
            self.last_raw_response = err
            print(f"LLM_DIAG api_error={err}")
            return None

    def _to_algebraic(self, row: int, col: int) -> str:
        # row 0 -> 9, row 8 -> 1
        # col 0 -> a, col 8 -> i
        rank = 9 - row
        file = chr(ord('a') + col)
        return f"{file}{rank}"

    def _format_legal_moves_compact(self, moves: List[Move]) -> str:
        # Returns a comma-separated string of moves: "M0:e2,M1:e3h..."
        compact = []
        for idx, m in enumerate(moves):
            mid = f"M{idx}"
            if m.kind == "pawn" and m.to:
                dest = self._to_algebraic(m.to.row, m.to.col)
                compact.append(f"{mid}:{dest}")
            elif m.kind == "wall" and m.wall:
                # Wall notation: e2h (horizontal), e2v (vertical)
                # Using the top-left coordinate of the wall
                coord = self._to_algebraic(m.wall.row, m.wall.col)
                orient = "h" if m.wall.horizontal else "v"
                compact.append(f"{mid}:{coord}{orient}")
        return ", ".join(compact)

    def _generate_dense_ascii_board(self, state: Any) -> str:
        # 9x9 cells, so 17x17 grid to include gaps for walls
        # Grid coords: r*2, c*2 are cells
        # r*2+1 are horizontal gaps
        # c*2+1 are vertical gaps
        grid_h = 17
        grid_w = 17
        grid = [[" " for _ in range(grid_w)] for _ in range(grid_h)]
        
        # Fill cells with dots
        for r in range(9):
            for c in range(9):
                grid[r*2][c*2] = "."

        # Place pawns
        for i, p in enumerate(state.pawns):
            if 0 <= p.row < 9 and 0 <= p.col < 9:
                grid[p.row*2][p.col*2] = str(i + 1)

        # Place walls
        # Wall(r, c, h)
        # Horizontal: blocks (r,c)-(r+1,c) and (r,c+1)-(r+1,c+1)
        # Visually, it sits between row r and r+1.
        # It spans two cells width.
        # Top-left of wall is gap at (r*2+1, c*2) ?
        # Let's trace:
        # Wall at r=0, c=0, horiz.
        # Between row 0 and 1.
        # Spans col 0 and 1.
        # Grid rows: 0(cell), 1(gap), 2(cell).
        # So it occupies grid[1][0], grid[1][1](intersection), grid[1][2].
        # Actually, walls are 2 units long.
        # In Quoridor, a wall at (r,c) blocks:
        #   Horizontal: (r,c)|(r+1,c) AND (r,c+1)|(r+1,c+1)
        #   So it runs from gap (r,c) to gap (r,c+1)?
        #   Let's use standard visual:
        #   Wall at (0,0) H:
        #   . .
        #   ---
        #   . .
        #   It is in the gap row `r*2 + 1`.
        #   It starts at col `c*2` and goes to `c*2 + 2` (length 3 chars: "---")
        
        for w in state.walls:
            r, c, h = w
            if h:
                # Row index in grid: r*2 + 1
                # Col start: c*2
                # Length: covers col c and c+1.
                # c*2 is center of col c. c*2+2 is center of col c+1.
                # So it covers indices c*2, c*2+1, c*2+2
                gr = r * 2 + 1
                if 0 <= gr < grid_h:
                    for k in range(3):
                        gc = c * 2 + k
                        if 0 <= gc < grid_w:
                            grid[gr][gc] = "-"
            else:
                # Vertical
                # Col index in grid: c*2 + 1
                # Row start: r*2
                # Covers row r and r+1
                gc = c * 2 + 1
                if 0 <= gc < grid_w:
                    for k in range(3):
                        gr = r * 2 + k
                        if 0 <= gr < grid_h:
                            grid[gr][gc] = "|"

        # Add coordinates
        lines = []
        lines.append("   a b c d e f g h i")
        for r in range(9):
            # Cell row
            row_label = str(9 - r)
            row_content = "".join(grid[r*2])
            lines.append(f"{row_label}  {row_content}  {row_label}")
            
            # Gap row (if not last)
            if r < 8:
                gap_content = "".join(grid[r*2+1])
                lines.append(f"   {gap_content}")
        lines.append("   a b c d e f g h i")
        
        return "\n".join(lines)

    def _parse_response(self, text: str) -> Tuple[str | None, str | None]:
        try:
            # Handle markdown code blocks if present
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            obj = json.loads(text)
            if isinstance(obj, dict):
                move_id = obj.get("move_id")
                rationale = obj.get("rationale")
                if isinstance(move_id, str):
                    return move_id.strip(), rationale
        except Exception:
            return None, None
        return None, None

    def _get_goals_description(self, num_players: int) -> str:
        # P0 (Top) -> Row 8 (Bottom)
        # P1 (2P) (Bottom) -> Row 0 (Top)
        # P1 (4P) (Right) -> Col 0 (Left)
        # P2 (Bottom) -> Row 0 (Top)
        # P3 (Left) -> Col 8 (Right)
        
        goals = []
        goals.append("P1: Reach Row 1 (Bottom)") # Internal Row 8 -> Rank 1
        
        if num_players == 2:
            goals.append("P2: Reach Row 9 (Top)") # Internal Row 0 -> Rank 9
        else:
            goals.append("P2: Reach Col a (Left)") # Internal Col 0 -> File a
            goals.append("P3: Reach Row 9 (Top)") # Internal Row 0 -> Rank 9
            goals.append("P4: Reach Col i (Right)") # Internal Col 8 -> File i
            
        return ", ".join(goals)

    def _get_rules_summary(self, num_players: int) -> str:
        rules = [
            "1. Goal: Be the FIRST to reach your objective line. If another player reaches theirs first, you lose.",
            "2. Move pawn 1 step orthogonally.",
            "3. Jump over adjacent pawn (straight, or diagonal if blocked).",
            "4. Place wall to block path (must leave 1 path open).",
        ]
        if num_players == 4:
            rules.append("5. No double jumps allowed.")
        return "\n".join(rules)

    def choose_move(self, view: GameView) -> Move:
        moves = list(view.legal_moves())
        if not moves:
            raise RuntimeError("No legal moves available for LLM agent")
            
        state = view.state
        
        # Generate Compact Data
        ascii_board = self._generate_dense_ascii_board(state)
        compact_moves = self._format_legal_moves_compact(moves)
        
        # Compact State Info
        pawns_info = " ".join([f"P{i+1}:{self._to_algebraic(p.row, p.col)}" for i, p in enumerate(state.pawns)])
        walls_info = f"Walls:{state.shared_walls_remaining}"
        
        # Dynamic Goals & Rules
        goals_desc = self._get_goals_description(state.num_players)
        rules_desc = self._get_rules_summary(state.num_players)
        
        # Construct prompt
        user_prompt = (
            f"Rules:\n{rules_desc}\n\n"
            f"Goals:\n{goals_desc}\n\n"
            f"Board:\n{ascii_board}\n\n"
            f"State: {pawns_info} | {walls_info}\n"
            f"Moves: {compact_moves}\n\n"
            'Select move ID. JSON: {"rationale": "...", "move_id":"Mx"}'
        )
        
        print("\n--- LLM INPUT PROMPT ---")
        print(user_prompt)
        print("------------------------\n")

        # Attempt LLM selection
        for attempt in range(1, self.max_attempts + 1):
            raw = self._call_llm(user_prompt)
            if raw is None:
                break  # fallback
                
            move_id, rationale = self._parse_response(raw)
            if move_id is None:
                print(f"LLM_DIAG unparsable_response attempt={attempt} raw={raw}")
                continue
                
            try:
                idx = int(move_id[1:]) if move_id.startswith("M") else -1
            except ValueError:
                idx = -1
                
            if 0 <= idx < len(moves):
                chosen = moves[idx]
                print(f"\n[LLM Rationale]: {rationale}")
                print(f"[LLM Move]: {move_id}\n")
                return chosen
                
        # Fallback
        pawn_moves = [m for m in moves if m.kind == "pawn"]
        if pawn_moves:
            fallback = pawn_moves[0]
            print("LLM_FALLBACK move_kind=pawn auto_selected reason=no_valid_llm")
            return fallback
            
        fallback = random.choice(moves)
        print(f"LLM_FALLBACK move_kind={fallback.kind} auto_selected reason=no_valid_llm")
        return fallback
