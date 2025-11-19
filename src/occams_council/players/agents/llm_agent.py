from __future__ import annotations
import os
import json
import random
from typing import List, Optional
from .base import GameView
from ...engine.state import Move

_openai_client: Optional["OpenAI"] = None  # lazy init
_openai_init_error: Optional[str] = None


def _ensure_client() -> None:
    global _openai_client, _openai_init_error
    if _openai_client is not None or _openai_init_error is not None:
        return
    try:
        from openai import OpenAI  # type: ignore

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            _openai_init_error = "missing_api_key"
            return
        _openai_client = OpenAI(api_key=api_key)
    except Exception as e:  # pragma: no cover
        _openai_init_error = f"init_exception:{e}"  # capture reason


SYSTEM_PROMPT = (
    "You are an expert Quoridor player. You must choose a single legal move "
    'that maximizes strategic advantage. Respond ONLY with a compact JSON object: {\n  "move_id": "Mx"\n}. Do not add commentary.'
)


class LLMAgent:
    name = "LLM Bot"
    is_human = False

    def __init__(self, model: str | None = None, max_attempts: int = 3):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.max_attempts = max_attempts
        self.last_raw_response: str | None = None

    def _format_legal_moves(self, moves: List[Move]) -> List[dict]:
        formatted = []
        for idx, m in enumerate(moves):
            mid = f"M{idx}"
            if m.kind == "pawn" and m.to:
                formatted.append(
                    {
                        "id": mid,
                        "action": "move_pawn",
                        "to": {"row": m.to.row, "col": m.to.col},
                    }
                )
            elif m.kind == "wall" and m.wall:
                formatted.append(
                    {
                        "id": mid,
                        "action": "place_wall",
                        "anchor": {"row": m.wall.row, "col": m.wall.col},
                        "orientation": "H" if m.wall.horizontal else "V",
                    }
                )
        return formatted

    def _call_llm(self, moves_payload: List[dict], game_payload: dict) -> str | None:
        _ensure_client()
        if _openai_client is None:
            # Debug reason output once
            if _openai_init_error:
                print(f"LLM_DIAG no_client reason={_openai_init_error}")
            else:
                print("LLM_DIAG no_client reason=unknown")
            return None  # signal fallback
        user_prompt = (
            "Game state JSON:"
            + json.dumps(game_payload, separators=(",", ":"))
            + "\nLegal moves (array):"
            + json.dumps(moves_payload, separators=(",", ":"))
            + '\nSelect one by its id. Respond only with {"move_id":"Mx"}.'
        )
        try:
            resp = _openai_client.chat.completions.create(
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
        except Exception as e:  # pragma: no cover
            err = f"ERROR: {e}"
            self.last_raw_response = err
            print(f"LLM_DIAG api_error={err}")
            return None

    def _parse_move_id(self, text: str) -> str | None:
        try:
            obj = json.loads(text)
            if (
                isinstance(obj, dict)
                and "move_id" in obj
                and isinstance(obj["move_id"], str)
            ):
                return obj["move_id"].strip()
        except Exception:
            return None
        return None

    def choose_move(self, view: GameView) -> Move:
        moves = list(view.legal_moves())
        if not moves:
            raise RuntimeError("No legal moves available for LLM agent")
        moves_payload = self._format_legal_moves(moves)
        # Build minimal game snapshot (exclude legal moves duplication)
        state = view.state
        game_payload = {
            "schema": "quoridor.v1.partial",
            "current_player": state.current_player,
            "pawns": [{"row": p.row, "col": p.col} for p in state.pawns],
            "walls": [
                {"row": r, "col": c, "orientation": "H" if h else "V"}
                for (r, c, h) in sorted(state.walls)
            ],
            "shared_walls_remaining": state.shared_walls_remaining,
        }
        # Attempt LLM selection
        for attempt in range(1, self.max_attempts + 1):
            raw = self._call_llm(moves_payload, game_payload)
            if raw is None:
                break  # fallback
            move_id = self._parse_move_id(raw)
            if move_id is None:
                # Reprompt with explicit instruction
                print(f"LLM_DIAG unparsable_response attempt={attempt} raw={raw}")
                continue
            # Validate against moves list
            try:
                idx = int(move_id[1:]) if move_id.startswith("M") else -1
            except ValueError:
                idx = -1
            if 0 <= idx < len(moves):
                chosen = moves[idx]
                print(f"LLM_CHOSEN move_id={move_id} raw={raw}")
                return chosen
        # Fallback: deterministic or random selection
        # Prefer a pawn move to keep game progressing if available
        pawn_moves = [m for m in moves if m.kind == "pawn"]
        if pawn_moves:
            fallback = pawn_moves[0]
            print("LLM_FALLBACK move_kind=pawn auto_selected reason=no_valid_llm")
            return fallback
        fallback = random.choice(moves)
        print(
            f"LLM_FALLBACK move_kind={fallback.kind} auto_selected reason=no_valid_llm"
        )
        return fallback
