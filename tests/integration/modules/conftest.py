# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Pytest configuration for the module integration tests.

Puts the directory that contains ``ansible_collections`` on ``sys.path`` (so the
plugin/module imports resolve) and on ``ANSIBLE_COLLECTIONS_PATH`` (so the
``ansible-playbook`` subprocess can find the ``opsmill.infrahub`` collection).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

for _parent in Path(__file__).resolve().parents:
    if (_parent / "ansible_collections").is_dir():
        root = str(_parent)
        if root not in sys.path:
            sys.path.insert(0, root)
        existing = os.environ.get("ANSIBLE_COLLECTIONS_PATH", "")
        if root not in existing.split(os.pathsep):
            os.environ["ANSIBLE_COLLECTIONS_PATH"] = os.pathsep.join(p for p in (root, existing) if p)
        break
