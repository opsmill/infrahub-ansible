"""Pytest configuration for the processor integration tests.

Puts the directory that contains ``ansible_collections`` on ``sys.path`` so the
plugin's absolute imports resolve under plain pytest, regardless of nesting depth.
"""

from __future__ import annotations

import sys
from pathlib import Path

for _parent in Path(__file__).resolve().parents:
    if (_parent / "ansible_collections").is_dir():
        if str(_parent) not in sys.path:
            sys.path.insert(0, str(_parent))
        break
