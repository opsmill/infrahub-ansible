# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the branch module's create/exists/delete decision logic.

BranchModule.run() is driven end-to-end with a mocked client wrapper (no SDK,
no network), asserting changed/msg and which branch operations were invoked.
"""

from __future__ import annotations

from ansible_collections.opsmill.infrahub.plugins.module_utils.branch import BranchModule

BRANCH = "feature-x"


def _module(mocker, *, state, existing_branch):
    mod = BranchModule.__new__(BranchModule)
    mod.module = mocker.Mock()
    mod.module.check_mode = False
    mod.module.fail_json = mocker.Mock(side_effect=AssertionError("unexpected fail_json"))
    mod.module.exit_json = mocker.Mock()
    mod.check_mode = False
    mod.state = state
    mod.data = {"name": BRANCH, "description": "d", "sync_with_git": False}
    mod.client = mocker.Mock()
    # _get_branch -> client.fetch_branch(name=...)
    mod.client.fetch_branch.return_value = existing_branch
    return mod


def test_create_branch_marks_changed(mocker):
    mod = _module(mocker, state="present", existing_branch=None)
    mod.client.create_branch.return_value = mocker.Mock()

    mod.run()

    mod.client.create_branch.assert_called_once()
    assert mod.result["changed"] is True
    assert "created" in mod.result["msg"]


def test_existing_branch_is_idempotent(mocker):
    mod = _module(mocker, state="present", existing_branch=mocker.Mock())

    mod.run()

    mod.client.create_branch.assert_not_called()
    assert mod.result["changed"] is False
    assert "already exists" in mod.result["msg"]


def test_delete_existing_branch_marks_changed(mocker):
    mod = _module(mocker, state="absent", existing_branch=mocker.Mock())

    mod.run()

    mod.client.delete_branch.assert_called_once_with(name=BRANCH)
    assert mod.result["changed"] is True
    assert "deleted" in mod.result["msg"]


def test_delete_missing_branch_is_idempotent(mocker):
    mod = _module(mocker, state="absent", existing_branch=None)

    mod.run()

    mod.client.delete_branch.assert_not_called()
    assert mod.result["changed"] is False
    assert "already absent" in mod.result["msg"]
