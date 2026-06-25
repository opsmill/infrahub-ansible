# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Make the collection loadable by Ansible's inventory plugin loader.

The inventory unit tests drive the real ``opsmill.infrahub.inventory`` plugin
through ``inventory_loader`` so the options contributed by the ``constructed``
doc fragment (compose / keyed_groups / groups / strict / leading_separator) are
registered. That loader resolves collections from ``ANSIBLE_COLLECTIONS_PATH``.

Point it at the collection shim that the top-level ``tests/unit/conftest.py``
builds (a temp dir containing ``ansible_collections/opsmill/infrahub`` symlinked
to the repo). Using the shim — rather than walking parents for an
``ansible_collections`` directory — works regardless of where the repo is checked
out (in CI it is not nested under such a path). This is scoped to the inventory
tests (not the top-level conftest) so initialising the collection-aware plugin
loader does not affect the other unit tests' import paths.
"""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

import os
import tempfile
from pathlib import Path

_shim = str(Path(tempfile.gettempdir()) / "opsmill-infrahub-collection-shim")
_existing = os.environ.get("ANSIBLE_COLLECTIONS_PATH", "")
if _shim not in _existing.split(os.pathsep):
    os.environ["ANSIBLE_COLLECTIONS_PATH"] = os.pathsep.join(p for p in (_shim, _existing) if p)

# Initialise the collection-aware plugin loader against the path set above so
# inventory_loader.get("opsmill.infrahub.inventory") resolves the plugin.
from ansible.plugins.loader import init_plugin_loader

init_plugin_loader()
