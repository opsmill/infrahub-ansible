# Copyright (c) 2025 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import InfrahubclientWrapper
from ansible_collections.opsmill.infrahub.plugins.module_utils.node import NodeModule

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_mock_module(extra_params=None, check_mode=False, state="present"):
    """Return a mock AnsibleModule with sensible defaults."""
    params = {
        "api_endpoint": "http://localhost:8000",
        "token": "test-token",
        "state": state,
        "validate_certs": True,
        "timeout": 10,
        "kind": "NetworkCircuitContract",
        "data": {"contract_start": {"value": "2026-01-01"}},
        "branch": "main",
        "file_path": None,
        "fetch_file": False,
    }
    if extra_params:
        params.update(extra_params)

    mock_module = MagicMock()
    mock_module.params = params
    mock_module.check_mode = check_mode
    mock_module.fail_json.side_effect = SystemExit(1)
    return mock_module


def make_mock_client(existing_node=None, schema=None, probe_node=None, inherit_from=None):
    """Return a mock InfrahubclientWrapper."""
    mock_client = MagicMock()
    if schema is None:
        schema = MagicMock()
        schema.human_friendly_id = ["file_name"]
        schema.attribute_names = ["contract_start", "contract_end", "file_name"]
        schema.relationship_names = []
        schema.attributes = []
        schema.relationships = []
        schema.inherit_from = inherit_from if inherit_from is not None else ["CoreFileObject"]
    mock_client.fetch_single_schema.return_value = schema
    mock_client.fetch_single_node.return_value = existing_node
    if probe_node is not None:
        mock_client.client.create.return_value = probe_node
    return mock_client


def make_mock_node(checksum="abc123sha1", is_file=True, node_id="uuid-1234"):
    """Return a mock InfrahubNodeSync representing a CoreFileObject node."""
    node = MagicMock()
    node.checksum.value = checksum
    node.is_file_object.return_value = is_file
    node.id = node_id
    node.hfid = ["contract.pdf"]
    node.get_human_friendly_id.return_value = "contract.pdf"
    node.get_raw_graphql_data.return_value = {
        "id": node_id,
        "file_name": {"value": "contract.pdf"},
        "checksum": {"value": checksum},
    }
    node._schema = MagicMock()
    node._schema.attribute_names = ["contract_start", "contract_end"]
    node._schema.relationship_names = []
    return node


def capture_result(mock_module):
    """Set up exit_json to capture the result dict."""
    result = {}
    mock_module.exit_json.side_effect = lambda **kwargs: result.update(kwargs)
    return result


# ---------------------------------------------------------------------------
# T013(a): Create with file_path → changed: true
# ---------------------------------------------------------------------------


class TestCreateWithFilePath:
    @patch("ansible_collections.opsmill.infrahub.plugins.module_utils.node.InfrahubNodesProcessor")
    @patch("pathlib.Path.exists", return_value=True)
    def test_create_with_file_path_changed_true(self, mock_exists, MockProcessor):
        """Creating a new CoreFileObject node with file_path reports changed: true."""
        new_node = make_mock_node()
        mock_processor_instance = MockProcessor.return_value
        mock_processor_instance.create_node.return_value = new_node

        probe = MagicMock()
        probe.is_file_object.return_value = True
        mock_client = make_mock_client(existing_node=None, probe_node=probe)

        mock_module = make_mock_module(extra_params={"file_path": "/tmp/contract.pdf"})
        result = capture_result(mock_module)

        node_module = NodeModule(module=mock_module, client=mock_client)
        node_module.run()

        assert result.get("changed") is True
        new_node.upload_from_path.assert_called_once_with(Path("/tmp/contract.pdf"))
        mock_processor_instance.save_node.assert_called_once_with(node=new_node)

    @patch("ansible_collections.opsmill.infrahub.plugins.module_utils.node.InfrahubNodesProcessor")
    @patch("pathlib.Path.exists", return_value=True)
    def test_create_with_file_path_check_mode_no_upload(self, mock_exists, MockProcessor):
        """In check_mode, file is not uploaded (no upload_from_path call)."""
        new_node = make_mock_node()
        mock_processor_instance = MockProcessor.return_value
        mock_processor_instance.create_node.return_value = new_node

        probe = MagicMock()
        probe.is_file_object.return_value = True
        mock_client = make_mock_client(existing_node=None, probe_node=probe)

        mock_module = make_mock_module(extra_params={"file_path": "/tmp/contract.pdf"}, check_mode=True)
        result = capture_result(mock_module)

        node_module = NodeModule(module=mock_module, client=mock_client)
        node_module.run()

        assert result.get("changed") is True
        new_node.upload_from_path.assert_not_called()
        mock_processor_instance.save_node.assert_not_called()


# ---------------------------------------------------------------------------
# T013(b): Update with same file checksum → changed: false
# ---------------------------------------------------------------------------


class TestUpdateSameChecksum:
    @patch("os.path.exists", return_value=True)
    def test_update_same_checksum_no_attr_change_unchanged(self, mock_exists):
        """Re-running with same file and same attrs reports changed: false."""
        checksum = "deadbeef1234"
        existing_node = make_mock_node(checksum=checksum)

        mock_client = make_mock_client(existing_node=existing_node)
        mock_client.get_file_object_local_checksum.return_value = checksum

        mock_module = make_mock_module(
            extra_params={
                "file_path": "/tmp/contract.pdf",
                "data": {},
            }
        )
        capture_result(mock_module)

        # Simulate _update_object returning no diff (nothing changed)
        with patch.object(NodeModule, "_update_object", return_value=(existing_node, None)):
            node_module = NodeModule(module=mock_module, client=mock_client)
            node_module.result = {"changed": False}
            node_module.infrahub_node = existing_node
            node_module._ensure_object_exists(
                kind="NetworkCircuitContract",
                data={"data": {}},
                file_path="/tmp/contract.pdf",
            )

        assert node_module.result.get("changed") is False
        existing_node.upload_from_path.assert_not_called()


# ---------------------------------------------------------------------------
# T013(c): Update with different checksum → changed: true
# ---------------------------------------------------------------------------


class TestUpdateDifferentChecksum:
    @patch("os.path.exists", return_value=True)
    def test_update_different_checksum_changed_true(self, mock_exists):
        """Update with a different file checksum reports changed: true."""
        server_checksum = "old-checksum"
        local_checksum = "new-checksum"
        existing_node = make_mock_node(checksum=server_checksum)

        mock_client = make_mock_client(existing_node=existing_node)
        mock_client.get_file_object_local_checksum.return_value = local_checksum

        mock_module = make_mock_module(extra_params={"file_path": "/tmp/contract.pdf"})
        capture_result(mock_module)

        node_module = NodeModule(module=mock_module, client=mock_client)
        node_module.result = {"changed": False}
        node_module.infrahub_node = existing_node

        node_module._ensure_object_exists(
            kind="NetworkCircuitContract",
            data={"data": {}},
            file_path="/tmp/contract.pdf",
        )

        assert node_module.result.get("changed") is True
        existing_node.upload_from_path.assert_called_once_with(Path("/tmp/contract.pdf"))
        existing_node.save.assert_called_once()


# ---------------------------------------------------------------------------
# T013(d): Update attrs only (no file_path) → existing behavior
# ---------------------------------------------------------------------------


class TestUpdateAttrsOnlyNoFilePath:
    def test_update_attrs_only_no_file_path_delegates_to_super(self):
        """When file_path is omitted, _ensure_object_exists falls through to super()."""
        existing_node = make_mock_node()
        mock_client = make_mock_client(existing_node=existing_node)

        mock_module = make_mock_module()  # no file_path
        capture_result(mock_module)

        node_module = NodeModule(module=mock_module, client=mock_client)
        node_module.result = {"changed": False}
        node_module.infrahub_node = existing_node

        super_called = []

        def fake_super_ensure(kind, data):
            super_called.append(True)
            node_module.result["msg"] = f"{kind} contract.pdf already exists"

        with patch.object(
            NodeModule.__bases__[0],
            "_ensure_object_exists",
            side_effect=lambda kind, data: fake_super_ensure(kind, data),
        ):
            node_module._ensure_object_exists(
                kind="NetworkCircuitContract",
                data={"data": {}},
                file_path=None,
            )

        assert super_called, "super()._ensure_object_exists() was not called"


# ---------------------------------------------------------------------------
# T013(e): file_path on non-CoreFileObject kind → fail_json
# ---------------------------------------------------------------------------


class TestFilePathOnNonCoreFileObject:
    @patch("pathlib.Path.exists", return_value=True)
    def test_file_path_non_file_object_fails(self, mock_exists):
        """file_path on a non-CoreFileObject kind calls fail_json."""
        mock_client = make_mock_client(existing_node=None, inherit_from=[])
        mock_module = make_mock_module(
            extra_params={
                "kind": "BuiltinTag",
                "file_path": "/tmp/contract.pdf",
            }
        )

        node_module = NodeModule(module=mock_module, client=mock_client)
        with pytest.raises(SystemExit):
            node_module.run()

        mock_module.fail_json.assert_called_once()
        call_kwargs = mock_module.fail_json.call_args[1]
        assert "file_path" in call_kwargs.get("msg", "")
        assert "CoreFileObject" in call_kwargs.get("msg", "")


# ---------------------------------------------------------------------------
# T013(f): file_path pointing to nonexistent file → fail_json
# ---------------------------------------------------------------------------


class TestFilePathNonexistent:
    @patch("os.path.exists", return_value=False)
    def test_nonexistent_file_path_fails_before_api_call(self, mock_exists):
        """A file_path that doesn't exist on disk calls fail_json before any API call."""
        mock_client = make_mock_client()
        mock_module = make_mock_module(extra_params={"file_path": "/tmp/nonexistent.pdf"})

        node_module = NodeModule(module=mock_module, client=mock_client)
        with pytest.raises(SystemExit):
            node_module.run()

        mock_module.fail_json.assert_called_once()
        call_kwargs = mock_module.fail_json.call_args[1]
        assert "/tmp/nonexistent.pdf" in call_kwargs.get("msg", "")
        # Confirm no schema/node API calls were made before the error
        mock_client.fetch_single_schema.assert_not_called()


# ---------------------------------------------------------------------------
# T018: US2 — fetch_file tests
# ---------------------------------------------------------------------------


class TestFetchFile:
    @patch("ansible_collections.opsmill.infrahub.plugins.module_utils.node.InfrahubNodesProcessor")
    @patch("os.path.exists", return_value=True)
    def test_fetch_file_with_attr_update_returns_binary(self, mock_exists, MockProcessor):
        """fetch_file: true with an attr change → changed: true + binary present."""
        existing_node = make_mock_node()
        mock_client = make_mock_client(existing_node=existing_node)
        mock_client.fetch_file_content.return_value = {
            "binary": "dGVzdA==",
            "text": None,
        }

        # Simulate attrs changed (diff is non-None)
        with patch.object(
            NodeModule,
            "_update_object",
            return_value=(existing_node, {"before": {}, "after": {"contract_end": "2027-12-31"}}),
        ):
            mock_module = make_mock_module(
                extra_params={
                    "fetch_file": True,
                    "data": {"id": "uuid-1234", "contract_start": {"value": "2026-01-01"}},
                }
            )
            result = capture_result(mock_module)

            node_module = NodeModule(module=mock_module, client=mock_client)
            node_module.run()

        assert result.get("changed") is True
        assert result.get("binary") == "dGVzdA=="

    @patch("os.path.exists", return_value=True)
    def test_fetch_file_no_change_returns_binary(self, mock_exists):
        """fetch_file: true with no change → changed: false + binary still present."""
        existing_node = make_mock_node()
        mock_client = make_mock_client(existing_node=existing_node)
        mock_client.fetch_file_content.return_value = {"binary": "dGVzdA==", "text": None}

        # Simulate no diff (node unchanged)
        with patch.object(NodeModule, "_update_object", return_value=(existing_node, None)):
            mock_module = make_mock_module(
                extra_params={
                    "fetch_file": True,
                    "data": {"id": "uuid-1234", "contract_start": {"value": "2026-01-01"}},
                }
            )
            result = capture_result(mock_module)

            node_module = NodeModule(module=mock_module, client=mock_client)
            node_module.run()

        assert result.get("changed") is False
        assert result.get("binary") == "dGVzdA=="

    @patch("pathlib.Path.exists", return_value=True)
    def test_fetch_file_with_file_path_mutually_exclusive(self, mock_exists):
        """fetch_file: true + file_path → fails as mutually exclusive."""
        mock_client = make_mock_client(existing_node=None)
        mock_module = make_mock_module(extra_params={"file_path": "/tmp/contract.pdf", "fetch_file": True})

        node_module = NodeModule(module=mock_module, client=mock_client)
        with pytest.raises(SystemExit):
            node_module.run()

        mock_module.fail_json.assert_called_once()
        call_kwargs = mock_module.fail_json.call_args[1]
        assert "mutually exclusive" in call_kwargs.get("msg", "")

    def test_fetch_file_non_file_object_fails(self):
        """fetch_file: true on a non-CoreFileObject kind calls fail_json."""
        mock_client = make_mock_client(existing_node=None, inherit_from=[])
        mock_module = make_mock_module(extra_params={"kind": "BuiltinTag", "fetch_file": True})

        node_module = NodeModule(module=mock_module, client=mock_client)
        with pytest.raises(SystemExit):
            node_module.run()

        mock_module.fail_json.assert_called_once()
        call_kwargs = mock_module.fail_json.call_args[1]
        assert "fetch_file" in call_kwargs.get("msg", "")
        assert "CoreFileObject" in call_kwargs.get("msg", "")

    @patch("os.path.exists", return_value=True)
    def test_fetch_file_check_mode_no_download(self, mock_exists):
        """check_mode + fetch_file: true → no download, binary absent from result."""
        existing_node = make_mock_node()
        mock_client = make_mock_client(existing_node=existing_node)

        with patch.object(NodeModule, "_update_object", return_value=(existing_node, None)):
            mock_module = make_mock_module(extra_params={"fetch_file": True}, check_mode=True)
            result = capture_result(mock_module)

            node_module = NodeModule(module=mock_module, client=mock_client)
            node_module.run()

        assert "binary" not in result
        mock_client.fetch_file_content.assert_not_called()


# ---------------------------------------------------------------------------
# T024: US4 — state: absent on CoreFileObject node
# ---------------------------------------------------------------------------


class TestDeleteCoreFileObject:
    @patch("pathlib.Path.exists", return_value=True)
    def test_state_absent_existing_file_object_node_changed_true(self, mock_exists):
        """state: absent on an existing CoreFileObject node reports changed: true."""
        existing_node = make_mock_node()
        mock_client = make_mock_client(existing_node=existing_node)

        mock_module = make_mock_module(
            extra_params={"state": "absent", "file_path": "/tmp/contract.pdf", "data": {"id": "uuid-1234"}},
        )
        result = capture_result(mock_module)

        # Simulate _delete_object returning a diff (node was deleted)
        with patch.object(
            NodeModule,
            "_delete_object",
            return_value={"before": {"state": "present"}, "after": {"state": "absent"}},
        ):
            node_module = NodeModule(module=mock_module, client=mock_client)
            node_module.run()

        assert result.get("changed") is True

    @patch("pathlib.Path.exists", return_value=True)
    def test_state_absent_already_absent_changed_false(self, mock_exists):
        """state: absent when node does not exist reports changed: false."""
        mock_client = make_mock_client(existing_node=None)

        mock_module = make_mock_module(
            extra_params={"state": "absent", "file_path": "/tmp/contract.pdf", "data": {"id": "uuid-missing"}},
        )
        result = capture_result(mock_module)

        node_module = NodeModule(module=mock_module, client=mock_client)
        node_module.run()

        assert result.get("changed") is False


# ---------------------------------------------------------------------------
# Real SHA-1 checksum computation (no mocking of checksum logic)
# ---------------------------------------------------------------------------


class TestRealChecksumComputation:
    def test_static_method_returns_correct_sha1(self, tmp_path):
        """get_file_object_local_checksum computes real SHA-1 hex digest."""
        test_file = tmp_path / "test.bin"
        content = b"Hello, CoreFileObject!"
        test_file.write_bytes(content)

        result = InfrahubclientWrapper.get_file_object_local_checksum(str(test_file))

        expected = hashlib.sha1(content, usedforsecurity=False).hexdigest()
        assert result == expected
        assert len(result) == 40

    def test_identical_content_same_checksum(self, tmp_path):
        """Same file content always produces the same checksum."""
        file_a = tmp_path / "a.txt"
        file_b = tmp_path / "b.txt"
        file_a.write_bytes(b"identical content")
        file_b.write_bytes(b"identical content")

        assert InfrahubclientWrapper.get_file_object_local_checksum(
            str(file_a)
        ) == InfrahubclientWrapper.get_file_object_local_checksum(str(file_b))

    def test_different_content_different_checksum(self, tmp_path):
        """Different file content produces different checksums."""
        file_a = tmp_path / "a.txt"
        file_b = tmp_path / "b.txt"
        file_a.write_bytes(b"content version 1")
        file_b.write_bytes(b"content version 2")

        assert InfrahubclientWrapper.get_file_object_local_checksum(
            str(file_a)
        ) != InfrahubclientWrapper.get_file_object_local_checksum(str(file_b))

    def test_update_real_checksum_match_skips_upload(self, tmp_path):
        """When real local checksum matches server checksum, no upload occurs."""
        test_file = tmp_path / "contract.pdf"
        content = b"contract file content"
        test_file.write_bytes(content)

        real_checksum = hashlib.sha1(content, usedforsecurity=False).hexdigest()
        existing_node = make_mock_node(checksum=real_checksum)
        mock_client = make_mock_client(existing_node=existing_node)
        # Wire in the real static method instead of a mock
        mock_client.get_file_object_local_checksum = InfrahubclientWrapper.get_file_object_local_checksum

        mock_module = make_mock_module(extra_params={"file_path": str(test_file), "data": {}})
        capture_result(mock_module)

        with patch.object(NodeModule, "_update_object", return_value=(existing_node, None)):
            node_module = NodeModule(module=mock_module, client=mock_client)
            node_module.result = {"changed": False}
            node_module.infrahub_node = existing_node
            node_module._ensure_object_exists(
                kind="NetworkCircuitContract",
                data={"data": {}},
                file_path=str(test_file),
            )

        assert node_module.result.get("changed") is False
        existing_node.upload_from_path.assert_not_called()

    def test_update_real_checksum_mismatch_triggers_upload(self, tmp_path):
        """When real local checksum differs from server, upload occurs."""
        test_file = tmp_path / "contract.pdf"
        content = b"updated contract content"
        test_file.write_bytes(content)

        existing_node = make_mock_node(checksum="old-server-checksum-doesnt-match")
        mock_client = make_mock_client(existing_node=existing_node)
        mock_client.get_file_object_local_checksum = InfrahubclientWrapper.get_file_object_local_checksum

        mock_module = make_mock_module(extra_params={"file_path": str(test_file)})
        capture_result(mock_module)

        node_module = NodeModule(module=mock_module, client=mock_client)
        node_module.result = {"changed": False}
        node_module.infrahub_node = existing_node
        node_module._ensure_object_exists(
            kind="NetworkCircuitContract",
            data={"data": {}},
            file_path=str(test_file),
        )

        assert node_module.result.get("changed") is True
        existing_node.upload_from_path.assert_called_once_with(Path(str(test_file)))
        existing_node.save.assert_called_once()


# ---------------------------------------------------------------------------
# Schema-based version gating (CoreFileObject inherit_from validation)
# ---------------------------------------------------------------------------


class TestSchemaVersionGating:
    """Tests that file_path/fetch_file require CoreFileObject in schema.inherit_from.

    This mirrors the integration test for Infrahub < 1.8 where CoreFileObject
    is not available in the schema.
    """

    @patch("pathlib.Path.exists", return_value=True)
    def test_file_path_with_empty_inherit_from_fails(self, mock_exists):
        """Schema with empty inherit_from rejects file_path."""
        mock_client = make_mock_client(existing_node=None, inherit_from=[])
        mock_module = make_mock_module(
            extra_params={"kind": "BuiltinTag", "file_path": "/tmp/file.pdf"},
        )

        node_module = NodeModule(module=mock_module, client=mock_client)
        with pytest.raises(SystemExit):
            node_module.run()

        mock_module.fail_json.assert_called_once()
        msg = mock_module.fail_json.call_args[1]["msg"]
        assert "CoreFileObject" in msg
        assert "file_path" in msg

    @patch("pathlib.Path.exists", return_value=True)
    def test_file_path_with_unrelated_inherit_from_fails(self, mock_exists):
        """Schema inheriting from something other than CoreFileObject rejects file_path."""
        mock_client = make_mock_client(existing_node=None, inherit_from=["CoreNode"])
        mock_module = make_mock_module(
            extra_params={"kind": "BuiltinTag", "file_path": "/tmp/file.pdf"},
        )

        node_module = NodeModule(module=mock_module, client=mock_client)
        with pytest.raises(SystemExit):
            node_module.run()

        mock_module.fail_json.assert_called_once()
        assert "CoreFileObject" in mock_module.fail_json.call_args[1]["msg"]

    def test_fetch_file_with_empty_inherit_from_fails(self):
        """Schema with empty inherit_from rejects fetch_file."""
        mock_client = make_mock_client(existing_node=None, inherit_from=[])
        mock_module = make_mock_module(
            extra_params={"kind": "BuiltinTag", "fetch_file": True},
        )

        node_module = NodeModule(module=mock_module, client=mock_client)
        with pytest.raises(SystemExit):
            node_module.run()

        mock_module.fail_json.assert_called_once()
        msg = mock_module.fail_json.call_args[1]["msg"]
        assert "CoreFileObject" in msg
        assert "fetch_file" in msg

    @patch("ansible_collections.opsmill.infrahub.plugins.module_utils.node.InfrahubNodesProcessor")
    @patch("pathlib.Path.exists", return_value=True)
    def test_file_path_with_core_file_object_inherit_from_succeeds(self, mock_exists, MockProcessor):
        """Schema with CoreFileObject in inherit_from allows file_path."""
        new_node = make_mock_node()
        mock_processor_instance = MockProcessor.return_value
        mock_processor_instance.create_node.return_value = new_node

        mock_client = make_mock_client(existing_node=None, inherit_from=["CoreFileObject"])
        mock_module = make_mock_module(extra_params={"file_path": "/tmp/contract.pdf"})
        result = capture_result(mock_module)

        node_module = NodeModule(module=mock_module, client=mock_client)
        node_module.run()

        assert result.get("changed") is True
        mock_module.fail_json.assert_not_called()
