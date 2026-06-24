"""Shared pytest configuration for the collection's Python unit tests.

These tests import the plugin code via its absolute collection path
(``ansible_collections.opsmill.infrahub.plugins.module_utils...``), so the
directory that *contains* ``ansible_collections`` must be importable. Under
plain ``pytest`` (``uv run pytest tests/unit``) that directory is not on
``sys.path`` by default, so we add it here.
"""

from __future__ import annotations

import sys
from pathlib import Path

# tests/unit/conftest.py -> parents[5] is the directory holding `ansible_collections`.
_COLLECTIONS_PARENT = Path(__file__).resolve().parents[5]
if str(_COLLECTIONS_PARENT) not in sys.path:
    sys.path.insert(0, str(_COLLECTIONS_PARENT))
