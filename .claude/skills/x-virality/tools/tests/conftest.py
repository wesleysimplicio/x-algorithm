"""Add the tools/ directory to sys.path so tests can import scripts directly.

The skill lives under `.claude/skills/x-virality/`, and the leading dot makes
the parent directories invalid as Python packages. The tests therefore import
the scripts as top-level modules and rely on this conftest to make that work.
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
