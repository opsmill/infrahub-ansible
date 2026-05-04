"""
Root conftest.py — makes the collection importable as ansible_collections.opsmill.infrahub
when running pytest directly from the repo root (e.g. `uv run pytest tests/unit/`).

The collection root IS this repository. We create a symlink so that
ansible_collections/opsmill/infrahub → repo root, then add that parent directory
to sys.path. This mirrors what ansible-galaxy collection install does.
"""

from __future__ import annotations

import sys
from pathlib import Path


def pytest_configure(config: object) -> None:
    repo_root = Path(__file__).parent.resolve()
    collections_dir = repo_root / ".pytest_collections"
    link_target = collections_dir / "ansible_collections" / "opsmill" / "infrahub"
    link_target.parent.mkdir(parents=True, exist_ok=True)
    if not link_target.exists():
        link_target.symlink_to(repo_root)
    collections_str = str(collections_dir)
    if collections_str not in sys.path:
        sys.path.insert(0, collections_str)
