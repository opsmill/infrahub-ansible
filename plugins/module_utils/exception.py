# Copyright (c) 2023 Benoit Kohler
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function  # noqa: UP010

__metaclass__ = type  # noqa: UP001

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from ansible.module_utils.basic import Display

try:
    from infrahub_sdk.exceptions import (
        GraphQLError,
        SchemaNotFoundError,
        ServerNotReachableError,
        ServerNotResponsiveError,
    )
except ImportError as imp_exc:
    INFRAHUBCLIENT_IMPORT_ERROR = imp_exc
else:
    INFRAHUBCLIENT_IMPORT_ERROR = None


def handle_infrahub_exceptions_decorator(display: Display | None) -> Callable[[Callable], Callable]:
    return handle_infrahub_exceptions(display=display)


def handle_infrahub_exceptions(display: Display | None) -> Callable[[Callable], Callable]:
    """
    Decorator factory to handle Infrahub exceptions.

    Parameters:
        display (Display | None): Display object for logging errors.

    Returns:
        Callable[[Callable], Callable]: A decorator that handles Infrahub exceptions.
    """

    def decorator(func: Callable) -> Callable:
        """
        Decorator to handle Infrahub exceptions.

        Parameters:
            func (Callable): Function that requires exception handling.

        Returns:
            Callable: Wrapped function with exception handling.
        """

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except GraphQLError as exc:
                msg1 = f"A GraphQL error occurred while executing Infrahub operation. {args}"
                msg2 = f"Parameters: {kwargs}"
                if display:
                    display.warning(msg1)
                    display.debug(f"GraphQLError: {exc}")
                    display.verbose(msg2, caplevel=2)
            except SchemaNotFoundError as exc:
                msg1 = f"An error occurred while looking for a Schema in Infrahub. {args}"
                msg2 = f"Parameters: {kwargs}"
                if display:
                    display.warning(msg1)
                    display.debug(f"SchemaNotFoundError: {exc}")
                    display.verbose(msg2, caplevel=2)
            except (ServerNotReachableError, ServerNotResponsiveError) as exc:
                msg1 = f"Server became unreacheable or unresponsive while executing Infrahub operation. {args}"
                msg2 = f"Parameters: {kwargs}"
                if display:
                    display.error(msg1)
                    display.debug(f"ServerNotResponsiveError: {exc}")
                    display.verbose(msg2, caplevel=2)
            except Exception as exc:
                msg1 = f"An unexpected error occurred while executing Infrahub operation. {args}"
                msg2 = f"Parameters: {kwargs}"
                if display:
                    display.warning(msg1)
                    display.debug(f"Error: {exc}")
                    display.verbose(msg2, caplevel=2)

        return wrapper

    return decorator
