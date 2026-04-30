# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

import pytest
from ansible_collections.opsmill.infrahub.plugins.inventory.inventory import _mark_trusted

try:
    from ansible.template import is_trusted_as_template

    HAS_TRUST_API = True
except ImportError:
    HAS_TRUST_API = False


@pytest.mark.skipif(not HAS_TRUST_API, reason="ansible-core < 2.19 has no trust API")
def test_mark_trusted_marks_plain_string():
    result = _mark_trusted("router1")
    assert is_trusted_as_template(result)


@pytest.mark.skipif(not HAS_TRUST_API, reason="ansible-core < 2.19 has no trust API")
def test_mark_trusted_recurses_into_dict_and_list():
    attributes = {
        "name": "router1",
        "asn": 65001,
        "interfaces": [{"name": "eth0", "ip": "10.0.0.1/24"}],
        "tags": ("prod", "core"),
    }
    result = _mark_trusted(attributes)

    assert is_trusted_as_template(result["name"])
    assert is_trusted_as_template(result["interfaces"][0]["name"])
    assert is_trusted_as_template(result["interfaces"][0]["ip"])
    assert all(is_trusted_as_template(t) for t in result["tags"])
    # Non-string scalars round-trip unchanged.
    assert result["asn"] == 65001


def test_mark_trusted_preserves_non_string_scalars():
    # Works on every ansible-core version (no-op fallback on <2.19).
    result = _mark_trusted({"id": 42, "active": True, "ratio": 0.5, "missing": None})
    assert result == {"id": 42, "active": True, "ratio": 0.5, "missing": None}


def test_mark_trusted_handles_set_and_tuple():
    result_set = _mark_trusted({"a", "b"})
    assert isinstance(result_set, set)
    assert {str(s) for s in result_set} == {"a", "b"}

    result_tuple = _mark_trusted(("a", "b"))
    assert isinstance(result_tuple, tuple)
    assert len(result_tuple) == 2
