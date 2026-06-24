# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Make the collection loadable by Ansible's inventory plugin loader.

The unit tests drive the real ``opsmill.infrahub.inventory`` plugin through
``inventory_loader`` so that the options contributed by the ``constructed`` doc
fragment (compose / keyed_groups / groups / strict / leading_separator) are
registered. That loader resolves collections from ``ANSIBLE_COLLECTIONS_PATH``,
so point it at the directory that contains ``ansible_collections`` before any
Ansible import happens.
"""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

import os
from pathlib import Path

for _parent in Path(__file__).resolve().parents:
    if _parent.name == "ansible_collections":
        _root = str(_parent.parent)
        _existing = os.environ.get("ANSIBLE_COLLECTIONS_PATH", "")
        if _root not in _existing.split(os.pathsep):
            os.environ["ANSIBLE_COLLECTIONS_PATH"] = os.pathsep.join(p for p in (_root, _existing) if p)
        break

# Initialise the collection-aware plugin loader against the path set above so
# inventory_loader.get("opsmill.infrahub.inventory") resolves the plugin.
from ansible.plugins.loader import init_plugin_loader

init_plugin_loader()
