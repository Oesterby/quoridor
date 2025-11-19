# OccamsCouncil
NO space for AI slop. Do the job.
Quoridor Hotseat Prototype
-------------------------

This repository contains a minimal Quoridor implementation with a Pygame hotseat UI. Two human players alternate turns placing pawns and walls.

Run Instructions
----------------

1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies.
3. Launch the hotseat game.

Commands (PowerShell) (Option A - quick run):

```
python -m venv .venv
& .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_hotseat.py

Editable Install (Option B - preferred for development):

```
pip install -e .
python run_hotseat.py
```

After editable install you can also run:

```
python -m occams_council.render.pygame_renderer
```
```

Controls
--------
- Left Click: Move pawn to a highlighted square.
- Shift + Left Click: Place a wall at the clicked cell anchor (uses current orientation).
- Space: Toggle wall orientation (H/V).
- Esc: Quit.

LLM Agent (Optional)
--------------------
You can pit a local player or random bot against an LLM. Set your OpenAI key before launching:

```
PowerShell:
$Env:OPENAI_API_KEY="sk-..."
$Env:OPENAI_MODEL="gpt-4o-mini"  # optional override
```

Install deps (includes `openai`):

```
pip install -r requirements.txt
```

Key bindings for agent configurations:

- 5: Human vs LLM
- 6: LLM vs Human
- 7: Random vs LLM
- 8: LLM vs Random
- 9: LLM vs LLM

If no API key is set the LLM Bot falls back to a simple deterministic move.

.env Alternative
----------------
Instead of setting environment variables manually, create a `.env` file in the repository root (same folder as `run_hotseat.py`):

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

`run_hotseat.py` loads this file automatically on start (keys in the actual environment are not overridden).

Next Steps
----------
- Heuristic/search-based agents.
- Path evaluation metrics (shortest path lengths).
- Caching for move generation performance.
- Automated tests for rules and pathfinding.
