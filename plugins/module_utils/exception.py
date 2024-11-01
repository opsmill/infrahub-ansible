# -*- coding: utf-8 -*-
# Copyright (c) 2023 Benoit Kohler
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


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


def handle_infrahub_exceptions(func):
    """
    Decorator function to handle exceptions for Infrahub operations.

    Parameters:
        func (Callable): Function that requires exception handling.

    Returns:
        Callable: Wrapped function with exception handling.
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except GraphQLError:
            raise Exception(f"An error occurred while executing the GraphQL Query {kwargs}")
        except SchemaNotFoundError:
            raise Exception(f"Unable to find the schema {kwargs}")
        except ServerNotReachableError:
            raise Exception("Server not Reacheable")
        except ServerNotResponsiveError:
            raise Exception("Server not Responsive")
        return None

    return wrapper
