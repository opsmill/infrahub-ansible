# Copyright (c) 2023 Benoit Kohler
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = """
    name: inventory
    author:
        - Benoit Kohler (@bearchitek)
    short_description: Infrahub inventory source (using GraphQL)
    description:
        - Get inventory hosts from Infrahub
    options:
        plugin:
            description: token that ensures this is a source file for the 'infrahub.infrahub' plugin.
            required: True
            choices: ['infrahub.infrahub.inventory']
        api_endpoint:
            description: Endpoint of the Infrahub API
            required: True
            env:
                - name: INFRAHUB_API
        token:
            required: True
            description: Infrahub API token to be able to read against Infrahub.
            env:
                - name: INFRAHUB_TOKEN
        query:
            required: False
            description: GraphQL query parameters or filters to send to Infrahub to obtain desired data
            type: dict
            default: {}
"""

EXAMPLES = """
# inventory.yml file in YAML format
# Example command line: ansible-inventory -v --list -i .yml
# Add -vvv to the command to also see the GraphQL query that gets sent in the debug output.
# Add -vvvv to the command to also see the JSON response that comes back in the debug output.

# Minimum required parameters
plugin: infrahub.infrahub.inventory
api_endpoint: http://localhost:8000  # Can be omitted if the INFRAHUB_API or INFRAHUB_URL environment variable is set
token: 1234567890123456478901234567  # Can be omitted if the INFRAHUB_TOKEN or INFRAHUB_API_KEY environment variable is set
"""

RETURN = """
  _list:
    description:
      - list of composed dictionaries with key and value
    type: list
"""
import json
from sys import version as python_version

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.module_utils._text import to_native, to_text
from ansible.module_utils.ansible_release import __version__ as ansible_version
from ansible.module_utils.six.moves.urllib import error as urllib_error
from ansible.module_utils.urls import open_url
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    NAME = "infrahub.infrahub.inventory"

    def main(self):
        """Main function."""

        base_query = {
            "query": {
                "devices": {
                    "name": None,
                }
            }
        }
        query = str(base_query)
        data = {"query": query}
        self.display.vvv(f"GraphQL query:\n{query}")

        try:
            response = open_url(
                self.api_endpoint + "/graphql/",
                method="post",
                data=json.dumps(data),
                headers=self.headers,
                timeout=self.timeout,
                validate_certs=self.validate_certs,
                follow_redirects=self.follow_redirects,
            )
        except urllib_error.HTTPError as err:
            raise AnsibleError(to_native(err.fp.read()))

        try:
            raw_data = to_text(response.read(), errors="surrogate_or_strict")
        except UnicodeError:
            raise AnsibleError(
                "Incorrect encoding of fetched payload from Infrahub API."
            )

        try:
            json_data = json.loads(raw_data)
        except ValueError:
            raise AnsibleError("Incorrect JSON payload: %s" % raw_data)

        self.display.vvvv(f"JSON response: {json_data}")

        # Error handling in case of a malformed query
        if "errors" in json_data:
            raise AnsibleParserError(to_native(json_data["errors"][0]["message"]))

    def _set_authorization(self):
        # Infrahub access
        if version.parse(ansible_version) < version.parse("2.11"):
            token = self.get_option("token")
        else:
            self.templar.available_variables = self._vars
            token = self.templar.template(
                self.get_option("token"), fail_on_undefined=False
            )
        if token:
            # check if token is new format
            if isinstance(token, dict):
                self.headers.update(
                    {"Authorization": f"{token['type'].capitalize()} {token['value']}"}
                )
            else:
                self.headers.update({"Authorization": "Token %s" % token})

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path)
        self._read_config_data(path=path)
        self.use_cache = cache

        self.api_endpoint = self.get_option("api_endpoint").strip("/")
        self.headers = {
            "User-Agent": "ansible %s Python %s"
            % (ansible_version, python_version.split(" ", maxsplit=1)[0]),
            "Content-type": "application/json",
        }
        self._set_authorization()

        self.query = self.get_option("query")

        self.main()
