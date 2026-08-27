# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""What ``InfrahubQueryProcessor.fetch_and_process`` says when a query does not work.

This is the lookup plugin's only error surface: ``lookup.py`` catches whatever comes
out of here and re-raises it as ``AnsibleError(str(exc))``, so a message that names
only the query is the whole of what a playbook author sees.

Two distinct failures reach this code, and they need different messages:

* ``execute_graphql`` raised -- the cause is the exception.
* ``execute_graphql`` returned ``None`` -- the wrapper's exception decorator logs and
  swallows whenever a ``Display`` is attached, which every plugin does, so a failed
  call arrives here as an empty return, with one line already logged: a warning for
  most failures, an error for an unreachable or unresponsive server, and the reason
  itself on that line only on the ``GraphQLError`` path.

The second is the one the shipped plugins take -- ``lookup.py`` and ``query_graphql.py``
both attach a ``Display`` -- so it is tested through the real decorator rather than
through a mock that raises where production never does.
"""

from __future__ import annotations

import pytest
from ansible_collections.opsmill.infrahub.plugins.module_utils import infrahub_utils as iu
from ansible_collections.opsmill.infrahub.plugins.module_utils.exception import handle_infrahub_exceptions_decorator
from infrahub_sdk.exceptions import GraphQLError, ServerNotResponsiveError

QUERY = {"ZoneBNG": {"edges": {"node": {"name": {"value": None}}}}}
RENDERED = "query { ZoneBNG { edges { node { name { value } } } } }"


def _processor(mocker, *, side_effect=None, return_value=None):
    """A query processor whose ``execute_graphql`` behaves as the test asks."""
    wrapper = mocker.MagicMock()
    wrapper._render_query.return_value = RENDERED
    wrapper.execute_graphql.side_effect = side_effect
    if side_effect is None:
        wrapper.execute_graphql.return_value = return_value
    return iu.InfrahubQueryProcessor(client=wrapper)


def _decorated_processor(error, display=None):
    """A query processor whose client is decorated the way the real wrapper decorates itself.

    A ``MagicMock`` raises whatever the test hands it, which is exactly what the
    production wrapper never does: ``InfrahubclientWrapper.__init__`` runs every
    public method through ``handle_infrahub_exceptions_decorator``, so the caller
    sees the decorator's output, not the SDK's. These tests reproduce that
    decoration rather than mocking past it.

    ``display`` picks which half of the decorator runs, and the two halves reach this
    code by different doors: with nothing attached it re-raises, so the failure arrives
    as an exception; with a ``Display`` attached it logs and returns ``None``, so the
    failure arrives as an empty response.
    """

    class _Client:
        def _render_query(self, query, variables=None):
            return RENDERED

        def execute_graphql(self, query, variables=None, branch=None):
            raise error

    client = _Client()
    client.execute_graphql = handle_infrahub_exceptions_decorator(display)(client.execute_graphql)
    return iu.InfrahubQueryProcessor(client=client)


def test_raised_failure_keeps_its_cause_and_message(mocker):
    """A GraphQL/transport failure survives to the caller instead of being replaced.

    The old code caught bare ``Exception`` and re-raised a message built only from the
    query, so the status code, the GraphQL error list or the timeout that actually
    explained the failure never reached the playbook.
    """
    original = RuntimeError("Server returned HTTP 502")
    processor = _processor(mocker, side_effect=original)

    with pytest.raises(Exception) as excinfo:
        processor.fetch_and_process(query=QUERY)

    # The cause is chained, so `-vvv` and any traceback still reach the real error.
    assert excinfo.value.__cause__ is original
    # And it is legible without a traceback, which is all AnsibleError(str(exc)) shows.
    assert "Server returned HTTP 502" in str(excinfo.value)
    assert "RuntimeError" in str(excinfo.value)


def test_decorated_graphql_error_is_named_not_the_wrapper_stand_in():
    """Through the real decorator, the reported type is ``GraphQLError``, not ``Exception``.

    With no ``Display`` attached the decorator re-raises the SDK error as a bare
    ``Exception(exc)``. Formatting that directly reported the type as "Exception" and
    chained ``__cause__`` to the stand-in, leaving the real error one level further
    away than the message and the traceback both claimed.
    """
    original = GraphQLError(errors=[{"message": "Zone 'bng' does not exist"}])
    processor = _decorated_processor(original)

    with pytest.raises(Exception) as excinfo:
        processor.fetch_and_process(query=QUERY)

    message = str(excinfo.value)
    assert "GraphQLError" in message
    assert "Zone 'bng' does not exist" in message
    assert "query: Exception:" not in message
    assert excinfo.value.__cause__ is original


def test_decorated_unexpected_error_keeps_its_own_type_and_cause():
    """The same holds for the decorator's catch-all branch, which goes through ``_handle_exc``."""
    original = RuntimeError("Server returned HTTP 502")
    processor = _decorated_processor(original)

    with pytest.raises(Exception) as excinfo:
        processor.fetch_and_process(query=QUERY)

    message = str(excinfo.value)
    assert "RuntimeError" in message
    assert "Server returned HTTP 502" in message
    assert excinfo.value.__cause__ is original


def test_empty_response_says_the_call_failed_not_that_the_query_is_bad(mocker):
    """``None`` back means the decorator swallowed a failure, and the message says so.

    ``handle_infrahub_exceptions`` logs and returns ``None`` whenever a ``Display`` is
    attached. Reporting that as a bad query sent people looking at their query text for
    a server-side problem. The message names the line that was logged and where the
    reason lives, without claiming the reason itself is already on screen.
    """
    processor = _processor(mocker, return_value=None)

    with pytest.raises(Exception) as excinfo:
        processor.fetch_and_process(query=QUERY)

    message = str(excinfo.value)
    assert "no response" in message.lower()
    # Points at the line the decorator logged, rather than echoing the query back.
    assert "logged above" in message.lower()
    assert RENDERED not in message
    # Both levels are named: `handle_infrahub_exceptions` reports an unreachable or
    # unresponsive server through ``display.error`` and everything else through
    # ``display.warning``, so naming only one sends half the authors looking for a
    # line that was never logged.
    assert "warning" in message.lower()
    assert "error" in message.lower()
    # Outside the ``GraphQLError`` path that logged line is only a generic prefix --
    # the reason sits behind ``display.verbose(..., caplevel=2)``. So the message
    # routes people to -vvv instead of claiming the reason was already printed.
    assert "-vvv" in message
    assert "reported above" not in message.lower()


def test_display_attached_failure_arrives_as_an_empty_response(mocker):
    """The path the shipped plugins actually take, pinned through the real decorator.

    ``lookup.py`` and ``query_graphql.py`` both build their wrapper with ``display=Display()``,
    so for them ``execute_graphql`` never raises at all: the decorator reports the failure
    and hands back nothing. The raising tests above pin a door those two never come through,
    and the empty-response message is the whole of what they show a playbook author.
    """
    display = mocker.MagicMock()
    processor = _decorated_processor(RuntimeError("Server returned HTTP 502"), display=display)

    with pytest.raises(Exception) as excinfo:
        processor.fetch_and_process(query=QUERY)

    message = str(excinfo.value)
    assert "no response" in message.lower()
    assert "logged above" in message.lower()
    assert "-vvv" in message
    # And the reason really is not on the logged line: the catch-all branch keeps it
    # behind `display.verbose(..., caplevel=2)`, which is why the message says -vvv
    # rather than telling people to read a reason that was never printed.
    display.warning.assert_called_once()
    assert "Server returned HTTP 502" not in display.warning.call_args[0][0]
    display.verbose.assert_any_call("Full error: Server returned HTTP 502", caplevel=2)


def test_display_attached_graphql_error_puts_the_reason_on_screen(mocker):
    """The one branch where the reason is already visible without ``-vvv``.

    ``GraphQLError`` is handled ahead of the catch-all and logs a second warning carrying
    the server's own message. The swallowed call still arrives here as an empty response,
    so the message does not change -- its ``-vvv`` pointer is a floor, not a claim that
    the reason is missing.
    """
    display = mocker.MagicMock()
    original = GraphQLError(errors=[{"message": "Zone 'bng' does not exist"}])
    processor = _decorated_processor(original, display=display)

    with pytest.raises(Exception) as excinfo:
        processor.fetch_and_process(query=QUERY)

    assert "no response" in str(excinfo.value).lower()
    display.warning.assert_any_call("Reason: Zone 'bng' does not exist")


def test_display_attached_unresponsive_server_is_logged_as_an_error(mocker):
    """The message sends authors looking for a warning *or* an error; this is the error.

    ``_handle_exc`` escalates to ``display.error`` for an unreachable or unresponsive
    server and never logs a warning for it. Naming only one of the two levels would send
    half the authors hunting for a line that was never logged, so both halves of that
    sentence need to stay true.
    """
    display = mocker.MagicMock()
    processor = _decorated_processor(ServerNotResponsiveError(url="https://infrahub.example"), display=display)

    with pytest.raises(Exception) as excinfo:
        processor.fetch_and_process(query=QUERY)

    assert "no response" in str(excinfo.value).lower()
    display.error.assert_called_once()
    display.warning.assert_not_called()


def test_typo_free_message(mocker):
    """The word is "GraphQL". Pinned because the old message shipped `grapqhl`."""
    processor = _processor(mocker, side_effect=RuntimeError("boom"))

    with pytest.raises(Exception) as excinfo:
        processor.fetch_and_process(query=QUERY)

    assert "grapqhl" not in str(excinfo.value)


def test_successful_query_is_returned_unchanged(mocker):
    """The happy path is untouched: a query response comes back as-is."""
    payload = {"ZoneBNG": {"edges": [{"node": {"name": {"value": "bng-01"}}}]}}
    processor = _processor(mocker, return_value=payload)

    assert processor.fetch_and_process(query=QUERY) == payload
