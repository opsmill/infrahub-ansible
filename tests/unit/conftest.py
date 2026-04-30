# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Pytest bootstrap for the opsmill.infrahub collection unit tests.

Ansible plugins inside the collection use absolute imports of the form
``ansible_collections.opsmill.infrahub.plugins.<...>``. Outside of
``ansible-test units``, that namespace is not on ``sys.path`` by default, so
this conftest creates a transient ``ansible_collections/opsmill/infrahub``
namespace that points at the repository root before any test module is
collected.
"""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

import contextlib
import sys
import tempfile
from pathlib import Path


def _bootstrap_collection_namespace() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    base = Path(tempfile.gettempdir()) / "opsmill-infrahub-collection-shim"
    target = base / "ansible_collections" / "opsmill" / "infrahub"

    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(FileExistsError):
            target.symlink_to(repo_root, target_is_directory=True)

    shim = str(base)
    if shim not in sys.path:
        sys.path.insert(0, shim)


_bootstrap_collection_namespace()
