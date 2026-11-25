"""Unit tests for ``InfrahubclientWrapper.fetch_single_artifact``."""

from __future__ import annotations

from ansible_collections.opsmill.infrahub.plugins.module_utils import infrahub_utils as iu


def test_missing_artifact_returns_empty_result(mocker):
    """No matching artifact gives an empty dict, which artifact_fetch reports as "unable to find"."""
    wrapper = iu.InfrahubclientWrapper.__new__(iu.InfrahubclientWrapper)
    wrapper.client = mocker.MagicMock()
    mocker.patch.object(wrapper, "fetch_single_node", return_value=None)

    assert wrapper.fetch_single_artifact(filters={"name__value": "missing"}) == {}
    wrapper.client._get.assert_not_called()
