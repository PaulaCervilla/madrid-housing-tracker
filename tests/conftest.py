"""Shared pytest fixtures."""
from __future__ import annotations

import sys
from pathlib import Path

# Make `import config` and `from src...` work in tests.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
