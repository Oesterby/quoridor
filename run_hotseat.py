import sys
import os


def load_dotenv(env_path: str) -> None:
    """Minimal .env loader (KEY=VALUE per line, ignores comments)."""
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                # Don't override if already set in environment
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass  # fail silent; not critical


# Ensure src layout is on path when running directly from repo root.
ROOT = os.path.dirname(__file__)
SRC = os.path.join(ROOT, "src")
load_dotenv(os.path.join(ROOT, ".env"))
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from occams_council.render.pygame_renderer import main

if __name__ == "__main__":
    main()
