# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""What a run cost, counted where the cost is actually incurred.

The inventory's expense is round-trips, and the number that matters is the one a
network trace would show. That number is not visible from the collection: the SDK
paginates inside ``client.filters()``, below ``InfrahubclientWrapper``, so counting
the calls the wrapper makes reports fetch *operations* and misses exactly the thing
that varies.

The SDK's ``Recorder`` protocol is invoked once per HTTP response, below pagination.
Implementing it is therefore the only place a truthful count can be taken, and it is
a supported extension point rather than a monkeypatch -- nothing is reassigned on the
client at runtime.

``httpx`` is annotated under ``TYPE_CHECKING`` so this module imports cleanly without
the SDK installed, the way every plugin file here has to.
"""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx


class RequestCounter:
    """Counts HTTP responses the SDK receives.

    Structurally a ``Recorder``: the SDK's protocol is runtime-checkable and asks
    only for ``record(response)``, so this satisfies it without importing it.

    The count covers *every* response, not only GraphQL ones -- schema lookups go
    over REST and cost a round-trip just the same. Reporting the smaller,
    GraphQL-only figure would understate what the run actually asked of the server.
    """

    def __init__(self) -> None:
        self.responses = 0

    def record(self, response: httpx.Response) -> None:  # noqa: ARG002
        """Called by the SDK for each response. The response itself is not retained."""
        self.responses += 1

    def reset(self) -> None:
        """Zero the counter. Useful when one client serves several measured runs."""
        self.responses = 0

    def __repr__(self) -> str:
        return f"{type(self).__name__}(responses={self.responses})"


def request_count(client_wrapper: Any) -> int | None:
    """The responses counted so far, or ``None`` when no counter is attached.

    A wrapper built through ``__new__`` -- which the integration tests do, to skip
    re-authenticating -- has no counter. Callers report what they can rather than
    failing over a missing diagnostic.
    """
    counter = getattr(client_wrapper, "request_counter", None)
    responses = getattr(counter, "responses", None)
    return responses if isinstance(responses, int) else None
