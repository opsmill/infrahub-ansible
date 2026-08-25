# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Pytest configuration for the module integration tests.

The collection-path and readiness handling lives in ``_harness`` so all three
integration suites share one copy of it; see that module for why either is needed.
"""

from __future__ import annotations

import sys
from pathlib import Path

# `tests/integration` is normally already on sys.path (this directory is a package,
# so pytest inserts its parent), but not when this suite is run on its own.
_INTEGRATION_ROOT = str(Path(__file__).resolve().parent.parent)
if _INTEGRATION_ROOT not in sys.path:
    sys.path.insert(0, _INTEGRATION_ROOT)

from _harness import infrahub_ready, install_collection_path, schema_loader

__all__ = ["infrahub_ready", "schema_loader"]

install_collection_path()
