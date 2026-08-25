# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit cover for the integration harness's collection staging.

The staging branch only runs where no ancestor directory provides the
``ansible_collections`` layout -- which is every CI checkout and no developer
checkout. That is exactly the shape of thing that stays broken for weeks, so it
is asserted here, in the suite that runs on every pull request, rather than only
in the nightly that needs docker.
"""

from __future__ import annotations

import sys
from pathlib import Path

_INTEGRATION_ROOT = Path(__file__).resolve().parents[1] / "integration"
if str(_INTEGRATION_ROOT) not in sys.path:
    sys.path.insert(0, str(_INTEGRATION_ROOT))

import _harness

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_staging_puts_the_collection_where_ansible_looks_for_it():
    """`opsmill.infrahub` only resolves from a `<root>/ansible_collections/opsmill/infrahub` path."""
    staging = _harness._staged_collection_root()

    link = staging.joinpath(*_harness.COLLECTION_PATH)
    assert link.is_symlink()
    # Resolving through the link has to reach this checkout's real plugin files.
    assert (link / "plugins" / "inventory" / "inventory.py").is_file()
    assert (link / "plugins" / "module_utils" / "infrahub_utils.py").is_file()


def test_staging_lives_outside_the_repository():
    """A link planted inside the repo would point at its own ancestor.

    The collection loader walks the tree it is given; a self-referential link makes
    that walk descend through the checkout into itself.
    """
    staging = _harness._staged_collection_root()

    assert REPO_ROOT not in staging.parents
    assert staging != REPO_ROOT


def test_collection_root_prefers_an_existing_layout():
    """A developer checkout already sits under `ansible_collections`; don't stage over it."""
    root = _harness.collection_root()

    assert (root / "ansible_collections").is_dir()
    assert (root / "ansible_collections" / "opsmill" / "infrahub").is_dir()
