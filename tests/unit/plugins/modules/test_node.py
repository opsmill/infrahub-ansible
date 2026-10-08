# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the node module's create/update/delete decision logic.

The SDK is never contacted: the client wrapper is a Mock, and NodeModule is
constructed without its __init__ (which would build a real client). We assert
the module's value-add — changed / diff / msg / state handling and check_mode
suppression of writes.
"""

from __future__ import annotations

import pytest
from ansible_collections.opsmill.infrahub.plugins.module_utils.node import NodeModule

KIND = "TestingThing"


def _module(mocker, *, state="present", check_mode=False, infrahub_node=None):
    """Build a NodeModule with mocked module + client, bypassing __init__."""
    mod = NodeModule.__new__(NodeModule)
    mod.module = mocker.Mock()
    mod.module.check_mode = check_mode
    # Any unexpected error path routes through fail_json — make it loud.
    mod.module.fail_json = mocker.Mock(side_effect=AssertionError("unexpected fail_json"))
    mod.check_mode = check_mode
    mod.state = state
    mod.wrapper = mocker.Mock()
    mod.result = {"changed": False}
    mod.infrahub_node = infrahub_node
    return mod


def _node(mocker, node_id="abc123"):
    node = mocker.Mock()
    node.hfid = None  # get_node_identifier falls back to id
    node.id = node_id
    return node


# --- decision logic: create / update / already-exists / absent -------------


def test_create_marks_changed(mocker):
    mod = _module(mocker, infrahub_node=None)
    node = _node(mocker)
    diff = {"before": {"state": "absent"}, "after": {"state": "present"}}
    mocker.patch.object(mod, "_create_object", return_value=(node, diff))

    mod._ensure_object_exists(kind=KIND, data={"data": {"name": "thing1"}})

    assert mod.result["changed"] is True
    assert "created" in mod.result["msg"]
    assert mod.result["diff"] == diff


def test_update_with_diff_marks_changed(mocker):
    node = _node(mocker)
    mod = _module(mocker, infrahub_node=node)
    diff = {"before": {"description": "old"}, "after": {"description": "new"}}
    mocker.patch.object(mod, "_update_object", return_value=(node, diff))

    mod._ensure_object_exists(kind=KIND, data={"data": {"description": "new"}})

    assert mod.result["changed"] is True
    assert "updated" in mod.result["msg"]
    assert mod.result["diff"] == diff


def test_update_without_diff_is_idempotent(mocker):
    node = _node(mocker)
    mod = _module(mocker, infrahub_node=node)
    mocker.patch.object(mod, "_update_object", return_value=(node, None))

    mod._ensure_object_exists(kind=KIND, data={"data": {"name": "thing1"}})

    assert mod.result["changed"] is False
    assert "already exists" in mod.result["msg"]


def test_absent_deletes_existing(mocker):
    node = _node(mocker)
    mod = _module(mocker, state="absent", infrahub_node=node)
    diff = {"before": {"state": "present"}, "after": {"state": "absent"}}
    mocker.patch.object(mod, "_delete_object", return_value=diff)

    mod._ensure_object_absent(kind=KIND, data={"data": {"name": "thing1"}})

    assert mod.result["changed"] is True
    assert "deleted" in mod.result["msg"]
    assert mod.result["diff"] == diff


def test_absent_on_missing_is_idempotent(mocker):
    mod = _module(mocker, state="absent", infrahub_node=None)

    mod._ensure_object_absent(kind=KIND, data={"data": {"name": "thing1"}})

    assert mod.result["changed"] is False
    assert "already absent" in mod.result["msg"]


# --- check_mode suppresses the actual write --------------------------------


@pytest.fixture
def _schema(mocker):
    schema = mocker.Mock()
    schema.attribute_names = ["name", "description"]
    schema.relationship_names = []
    schema.attributes = []  # no required attributes to validate
    schema.relationships = []
    return schema


def test_create_check_mode_does_not_save(mocker, _schema):
    mod = _module(mocker, check_mode=True)
    mod.wrapper.fetch_single_schema.return_value = _schema
    mod.wrapper.create_node.return_value = _node(mocker)

    mod._create_object(kind=KIND, data={"name": "thing1"})

    mod.wrapper.create_node.assert_called_once()
    mod.wrapper.save_node.assert_not_called()


def test_create_persists_when_not_check_mode(mocker, _schema):
    mod = _module(mocker, check_mode=False)
    mod.wrapper.fetch_single_schema.return_value = _schema
    mod.wrapper.create_node.return_value = _node(mocker)

    mod._create_object(kind=KIND, data={"name": "thing1"})

    mod.wrapper.save_node.assert_called_once()


def test_delete_check_mode_does_not_delete(mocker):
    mod = _module(mocker, state="absent", check_mode=True, infrahub_node=_node(mocker))

    mod._delete_object()

    mod.wrapper.delete_node.assert_not_called()


def test_delete_calls_client_when_not_check_mode(mocker):
    mod = _module(mocker, state="absent", check_mode=False, infrahub_node=_node(mocker))

    mod._delete_object()

    mod.wrapper.delete_node.assert_called_once()
