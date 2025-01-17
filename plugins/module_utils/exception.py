# Copyright (c) 2023 Benoit Kohler
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from typing import Any

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


def handle_infrahub_exceptions(func) -> None:  # noqa: ANN001
    """
    Decorator function to handle exceptions for Infrahub operations.

    Parameters:
        func (Callable): Function that requires exception handling.

    Returns:
        Callable: Wrapped function with exception handling.
    """

    def wrapper(*args: tuple, **kwargs: dict[str, Any]) -> None:
        try:
            return func(*args, **kwargs)
        except GraphQLError as exc:
            msg = f"An error occurred while executing the GraphQL Query. Parameters:{kwargs} Error: {exc}"
            raise Exception(msg)
        except SchemaNotFoundError as exc:
            msg = f"Unable to find the schema. Parameters:{kwargs} Error: {exc}"
            raise Exception(msg)
        except ServerNotReachableError as exc:
            msg = f"Server not Reacheable. Error: {exc}"
            raise Exception(msg)
        except ServerNotResponsiveError as exc:
            msg = f"Server not Responsive. Error: {exc}"
            raise Exception(msg)
        return None

    return wrapper
