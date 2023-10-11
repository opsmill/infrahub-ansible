# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Infrahub Action Plugin to Query GraphQL."""

from __future__ import absolute_import, division, print_function

from ansible.errors import AnsibleError
from ansible.module_utils.six import raise_from
from ansible.plugins.action import ActionBase

try:
    import requests
except ImportError as imp_exc:
    REQUESTS_IMPORT_ERROR = imp_exc
else:
    REQUESTS_IMPORT_ERROR = None

__metaclass__ = type


class ActionModule(ActionBase):
    """Ansible Action Module to interact with Infrahub GraphQL Endpoint.

    Args:
        ActionBase (ActionBase): Ansible Action Plugin
    """

    def run(self, tmp=None, task_vars=None):
        """Run of action plugin for interacting with Infrahub GraphQL API.

        Args:
            tmp ([type], optional): [description]. Defaults to None.
            task_vars ([type], optional): [description]. Defaults to None.
        """

        if REQUESTS_IMPORT_ERROR:
            raise_from(
                AnsibleError("requests must be installed to use this plugin"),
                REQUESTS_IMPORT_ERROR,
            )

        self._supports_check_mode = True
        self._supports_async = False

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp

        if result.get("skipped"):
            return None

        if result.get("invocation", {}).get("module_args"):
            # avoid passing to modules in case of no_log
            # should not be set anymore but here for backwards compatibility
            del result["invocation"]["module_args"]

        # do work!
        # Get the arguments from the module definition
        self._task.args
        try:
            results = None
            ## TODO
        except requests.exceptions.HTTPError as http_error:
            return {
                "failed": True,
                "msg": f"Request failed: {http_error}",
            }

        # Results should be the data response of the query to be returned as a lookup
        return results
