# Copyright (c) 2025 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from ansible.module_utils.basic import Display

try:
    from infrahub_sdk.exceptions import (
        BranchNotFoundError,
        GraphQLError,
        SchemaNotFoundError,
        ServerNotReachableError,
        ServerNotResponsiveError,
    )
except ImportError as imp_exc:
    INFRAHUBCLIENT_IMPORT_ERROR = imp_exc
else:
    INFRAHUBCLIENT_IMPORT_ERROR = None


def _handle_exc(
    exc: Exception,
    msg_prefix: str,
    kwargs: Any,
    display: Display | None,
    level: str | None = "warning",
) -> None:
    """
    Helper to log (or raise) exceptions.
    """
    msg1 = f"{msg_prefix}"
    msg2 = f"Parameters: {kwargs}"
    if display:
        if level == "error":
            display.error(msg1)
        else:
            display.warning(msg1)
        display.verbose(f"Full error: {exc}", caplevel=4)
        display.verbose(msg2, caplevel=2)
    elif exc.__class__ == BranchNotFoundError:
        raise exc
    else:
        raise Exception(exc)


def handle_infrahub_exceptions_decorator(display: Display | None) -> Callable[[Callable], Callable]:
    return handle_infrahub_exceptions(display=display)


def handle_infrahub_exceptions(display: Display | None) -> Callable[[Callable], Callable]:
    """
    Decorator factory to handle Infrahub exceptions.

    Parameters:
        display (Display | None): Display object for logging errors.

    Returns:
        Callable[[Callable], Callable]: A decorator that wraps a function with exception handling.
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except GraphQLError as exc:
                msg1 = f"A GraphQL error occurred while executing Infrahub operation. {args}"
                msg2 = f"Parameters: {kwargs}"
                error_msg = str(exc)
                if hasattr(exc, "errors"):
                    error_messages = []
                    for err in exc.errors:
                        if isinstance(err, dict):
                            error_messages.append(err.get("message", ""))
                        else:
                            error_messages.append(str(err))
                    error_msg = ", ".join(error_messages)
                if display:
                    display.warning(msg1)
                    display.warning(f"Reason: {error_msg}")
                    display.verbose(f"Full error: {exc}", caplevel=4)
                    display.verbose(msg2, caplevel=2)
                else:
                    raise Exception(exc)
            except SchemaNotFoundError as exc:
                _handle_exc(
                    display=display,
                    exc=exc,
                    msg_prefix=f"An error occurred while looking for a Schema in Infrahub. {args}",
                    kwargs=kwargs,
                )
            except BranchNotFoundError as exc:
                _handle_exc(
                    display=display,
                    exc=exc,
                    msg_prefix=f"An error occurred while looking for a Branch in Infrahub. {args}",
                    kwargs=kwargs,
                )
            except (ServerNotReachableError, ServerNotResponsiveError) as exc:
                _handle_exc(
                    display=display,
                    exc=exc,
                    msg_prefix=f"Server became unreachable or unresponsive while executing Infrahub operation. {args}",
                    kwargs=kwargs,
                    level="error",
                )
            except Exception as exc:
                _handle_exc(
                    display=display,
                    exc=exc,
                    msg_prefix=f"An unexpected error occurred while executing Infrahub operation. {args}",
                    kwargs=kwargs,
                )

        return wrapper

    return decorator
