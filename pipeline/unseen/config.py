"""Paths and constants. Override the cache folder with UNSEEN_DATA_DIR (e.g. in .env)."""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load_dotenv():
    """Minimal .env loader (repo root), so we don't need python-dotenv. Existing env vars win."""
    f = REPO / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

DATA_DIR = Path(os.environ.get("UNSEEN_DATA_DIR", REPO / "data"))   # caches (git-ignored)
EVENTS_DIR = Path(os.environ.get("UNSEEN_EVENTS_DIR", REPO / "events"))  # site bundles (committed, served by Vercel)

# NISAR
PROVISIONAL_START = "2026-06-17"     # first calibrated (PROVISIONAL) L-band acquisitions
MIN_DATES = 4                        # minimum dates for a usable stack
MIN_COVERAGE = 0.9                   # a granule must cover >= 90% of the bbox
MAX_DEG = 1.5                        # largest box side (degrees); runtime grows with area
