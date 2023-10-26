# -*- coding: utf-8 -*-
# Copyright (c) 2023 Benoit Kohler
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


try:
    from infrahub_client.exceptions import (
        FilterNotFound,
        GraphQLError,
        SchemaNotFound,
        ServerNotReacheableError,
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
            raise Exception("Database not Responsive")
        except SchemaNotFound:
            pass  # until we are able to return Generics Schema and Core Schema https://github.com/opsmill/infrahub/issues/1217
        except FilterNotFound:
            raise Exception(f"Filters not Found {kwargs}")
        except ServerNotReacheableError:
            raise Exception("Server not Reacheable")
        except ServerNotResponsiveError:
            raise Exception("Server not Responsive")
        return None

    return wrapper
