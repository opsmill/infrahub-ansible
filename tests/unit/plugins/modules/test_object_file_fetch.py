# Copyright (c) 2025 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from ansible_collections.opsmill.infrahub.plugins.action.object_file_fetch import ActionModule

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FILE_CONTENT = b"Hello, CoreFileObject!"
FILE_B64 = base64.b64encode(FILE_CONTENT).decode("ascii")


def make_mock_task(args=None):
    """Return a mock Ansible task."""
    default_args = {
        "api_endpoint": "http://localhost:8000",
        "token": "test-token",
        "kind": "NetworkCircuitContract",
        "node_id": "uuid-1234",
        "hfid": None,
        "dest": None,
        "branch": "main",
        "timeout": 10,
        "validate_certs": True,
    }
    if args:
        default_args.update(args)
    task = MagicMock()
    task.args = default_args
    return task


def make_mock_schema(inherit_from=None):
    """Return a mock schema with configurable inherit_from."""
    schema = MagicMock()
    schema.inherit_from = inherit_from if inherit_from is not None else ["CoreFileObject"]
    return schema


def make_mock_node(
    node_id="uuid-1234",
    file_name="contract.pdf",
    file_type="application/pdf",
    file_size=22,
    checksum="abc123sha1",
    is_file=True,
):
    """Return a mock InfrahubNodeSync for a CoreFileObject."""
    node = MagicMock()
    node.id = node_id
    node.file_name.value = file_name
    node.file_type.value = file_type
    node.file_size.value = file_size
    node.checksum.value = checksum
    node.is_file_object.return_value = is_file
    return node


def make_action_module(task=None):
    """Construct an ActionModule with a mocked task and connection."""
    if task is None:
        task = make_mock_task()

    action = ActionModule.__new__(ActionModule)
    action._task = task
    action._connection = MagicMock()
    action._play_context = MagicMock()
    action._loader = MagicMock()
    action._templar = MagicMock()
    action._shared_loader_obj = MagicMock()
    return action


# ---------------------------------------------------------------------------
# T022(a): Fetch by node_id → result contains binary + metadata
# ---------------------------------------------------------------------------


class TestFetchByNodeId:
    @patch("ansible_collections.opsmill.infrahub.plugins.action.object_file_fetch.InfrahubclientWrapper")
    @patch("ansible.plugins.action.ActionBase.run", return_value={})
    def test_fetch_by_node_id_returns_binary_and_metadata(self, mock_super_run, MockClient):
        """Fetching by node_id returns binary content and metadata fields."""
        node = make_mock_node()
        mock_client = MockClient.return_value
        mock_client.fetch_single_schema.return_value = make_mock_schema()
        mock_client.fetch_file_object.return_value = (node, FILE_CONTENT)

        action = make_action_module()
        result = action.run()

        assert result["binary"] == FILE_B64
        assert result["node_id"] == "uuid-1234"
        assert result["file_name"] == "contract.pdf"
        assert result["file_type"] == "application/pdf"
        assert result["checksum"] == "abc123sha1"
        assert result["dest"] is None

    @patch("ansible_collections.opsmill.infrahub.plugins.action.object_file_fetch.InfrahubclientWrapper")
    @patch("ansible.plugins.action.ActionBase.run", return_value={})
    def test_fetch_by_node_id_calls_fetch_file_object(self, mock_super_run, MockClient):
        """Fetching by node_id calls fetch_file_object with the right args."""
        node = make_mock_node()
        mock_client = MockClient.return_value
        mock_client.fetch_single_schema.return_value = make_mock_schema()
        mock_client.fetch_file_object.return_value = (node, FILE_CONTENT)

        action = make_action_module()
        action.run()

        mock_client.fetch_file_object.assert_called_once_with(
            kind="NetworkCircuitContract",
            node_id="uuid-1234",
            hfid=None,
            branch="main",
        )


# ---------------------------------------------------------------------------
# T022(b): Fetch by hfid → result contains binary + metadata
# ---------------------------------------------------------------------------


class TestFetchByHfid:
    @patch("ansible_collections.opsmill.infrahub.plugins.action.object_file_fetch.InfrahubclientWrapper")
    @patch("ansible.plugins.action.ActionBase.run", return_value={})
    def test_fetch_by_hfid_returns_binary_and_metadata(self, mock_super_run, MockClient):
        """Fetching by hfid returns binary content and metadata fields."""
        node = make_mock_node()
        mock_client = MockClient.return_value
        mock_client.fetch_single_schema.return_value = make_mock_schema()
        mock_client.fetch_file_object.return_value = (node, FILE_CONTENT)

        task = make_mock_task({"node_id": None, "hfid": ["contract.pdf"]})
        action = make_action_module(task=task)
        result = action.run()

        assert result["binary"] == FILE_B64
        assert result["file_name"] == "contract.pdf"
        mock_client.fetch_file_object.assert_called_once_with(
            kind="NetworkCircuitContract",
            node_id=None,
            hfid=["contract.pdf"],
            branch="main",
        )


# ---------------------------------------------------------------------------
# T022(c): dest as directory → file written to {dest}/{file_name}
# ---------------------------------------------------------------------------


class TestDestDirectory:
    @patch("ansible_collections.opsmill.infrahub.plugins.action.object_file_fetch.InfrahubclientWrapper")
    @patch("ansible.plugins.action.ActionBase.run", return_value={})
    def test_dest_directory_writes_file_and_sets_resolved_dest(self, mock_super_run, MockClient, tmp_path):
        """When dest is a directory, file is written to dest/file_name."""
        node = make_mock_node(file_name="contract.pdf")
        mock_client = MockClient.return_value
        mock_client.fetch_single_schema.return_value = make_mock_schema()
        mock_client.fetch_file_object.return_value = (node, FILE_CONTENT)

        dest_dir = str(tmp_path) + "/"
        task = make_mock_task({"dest": dest_dir})
        action = make_action_module(task=task)
        result = action.run()

        expected_dest = str(tmp_path / "contract.pdf")
        assert result["dest"] == expected_dest
        assert Path(expected_dest).read_bytes() == FILE_CONTENT


# ---------------------------------------------------------------------------
# T022(d): dest as file path → file written exactly at that path
# ---------------------------------------------------------------------------


class TestDestFilePath:
    @patch("ansible_collections.opsmill.infrahub.plugins.action.object_file_fetch.InfrahubclientWrapper")
    @patch("ansible.plugins.action.ActionBase.run", return_value={})
    def test_dest_file_path_writes_to_exact_path(self, mock_super_run, MockClient, tmp_path):
        """When dest is a file path, file is written exactly at that path."""
        node = make_mock_node()
        mock_client = MockClient.return_value
        mock_client.fetch_single_schema.return_value = make_mock_schema()
        mock_client.fetch_file_object.return_value = (node, FILE_CONTENT)

        dest_file = str(tmp_path / "my-contract.pdf")
        task = make_mock_task({"dest": dest_file})
        action = make_action_module(task=task)
        result = action.run()

        assert result["dest"] == dest_file
        assert Path(dest_file).read_bytes() == FILE_CONTENT


# ---------------------------------------------------------------------------
# T022(e): Neither node_id nor hfid → fail with AnsibleError
# ---------------------------------------------------------------------------


class TestMissingIdentifier:
    @patch("ansible.plugins.action.ActionBase.run", return_value={})
    def test_no_node_id_or_hfid_raises_ansible_error(self, mock_super_run):
        """Neither node_id nor hfid provided raises AnsibleError."""
        from ansible.errors import AnsibleError

        task = make_mock_task({"node_id": None, "hfid": None})
        action = make_action_module(task=task)

        with pytest.raises(AnsibleError, match=r"node_id.*hfid|hfid.*node_id"):
            action.run()


# ---------------------------------------------------------------------------
# T022(f): kind not CoreFileObject → fail with AnsibleError
# ---------------------------------------------------------------------------


class TestNonFileObjectKind:
    @patch("ansible_collections.opsmill.infrahub.plugins.action.object_file_fetch.InfrahubclientWrapper")
    @patch("ansible.plugins.action.ActionBase.run", return_value={})
    def test_non_file_object_kind_raises_ansible_error(self, mock_super_run, MockClient):
        """When the fetched node is not a CoreFileObject, AnsibleError is raised."""
        from ansible.errors import AnsibleError

        node = make_mock_node(is_file=False)
        mock_client = MockClient.return_value
        mock_client.fetch_single_schema.return_value = make_mock_schema(inherit_from=[])
        mock_client.fetch_file_object.return_value = (node, FILE_CONTENT)

        action = make_action_module()

        with pytest.raises(AnsibleError, match="CoreFileObject"):
            action.run()
