# -*- coding: utf-8 -*-
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
    extends_documentation_fragment:
        - constructed
        - inventory_cache
    options:
        plugin:
            description:
                - token that ensures this is a source file for the 'opsmill.infrahub' plugin.
            required: True
            choices: ['opsmill.infrahub.inventory']
        api_endpoint:
            description: Endpoint of the Infrahub API
            required: True
            env:
                - name: INFRAHUB_API
        token:
            required: True
            description:
                - Infrahub API token to be able to read against Infrahub.
            env:
                - name: INFRAHUB_TOKEN
        timeout:
            required: False
            description: Timeout for Infrahub requests in seconds
            type: int
            default: 10
        nodes:
            required: True
            description:
                - Configuration for specific node types within Infrahub.
                - Defines the attributes to include or exclude for each node.
            type: dict
            suboptions:
                node_type:
                    description:
                        - Configuration settings for a specific node type, e.g., "InfraDevice".
                        - Replace "node_type" with the actual node type name you want to configure.
                    type: dict
                    suboptions:
                        filters:
                            description:
                                - List of filters to apply on the query for node_type.
                            type: dict
                            default: {}
                        include:
                            description:
                                - List of attributes to include for node_type.
                            type: list
                            elements: str
                            default: []
                        exclude:
                            description:
                                - List of attributes to exclude for node_type.
                            type: list
                            elements: str
                            default: []
        branch:
            required: False
            description:
                - Branch in which the request is made
            type: str
            default: main
        compose:
            description:
                - List of custom ansible host vars to create from the objects fetched from Infrahub
            type: dict
            default: {}
        keyed_groups:
            required: False
            description:
                - Create groups based on attributes or relationships.
                - groups is created as attribute__value 
            type: list
            elements: str
            default: []
        validate_certs:
            description:
                - Whether or not to validate SSL of the Infrahub instance
            required: False
            default: True
"""

EXAMPLES = """
# inventory.yml file in YAML format
# Example command line: ansible-inventory -v --list -i .yml
# Add -vvv to the command to also see the GraphQL query that gets sent in the debug output.
# Add -vvvv to the command to also see the JSON response that comes back in the debug output.

# Minimum required parameters
plugin: opsmill.infrahub.inventory
api_endpoint: http://localhost:8000  # Can be omitted if the INFRAHUB_API environment variable is set
token: 1234567890123456478901234567  # Can be omitted if the INFRAHUB_TOKEN environment variable is set

# Complete Example
# This will :
# - Retrieve in the branch "branch1" attributes for the Node Kind "InfraDevice"
# - The attributes wanted for "InfraDevice" are forced with the keyword "include"
# - Create 2 compose variable "hostname" ad "platform" (platform will override the attribute platform retrieved)
# - Create group based on the "site" name

plugin: opsmill.infrahub.inventory
api_endpoint: "http://localhost:8000"
validate_certs: True

strict: True

branch: "branch1"

nodes:
  InfraDevice:
    include:
      - name
      - platform
      - primary_address
      - interfaces
      - site

compose:
  hostname: name
  platform: platform.ansible_network_os

keyed_groups:
  - prefix: site
    key: site.name
"""

RETURN = """
  _list:
    description:
      - list of composed dictionaries with key and value
    type: list
"""
import json
from typing import Any, Dict, Optional, Tuple

from ansible.errors import AnsibleError
from ansible.module_utils.six import raise_from
from ansible.module_utils.ansible_release import __version__ as ansible_version
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import (
    HAS_INFRAHUBCLIENT,
    INFRAHUBCLIENT_IMP_ERR,
    InfrahubclientWrapper,
    InfrahubNodesProcessor,
)

try:
    from packaging import version
except ImportError as imp_exc:
    PACKAGING_IMPORT_ERROR = imp_exc
else:
    PACKAGING_IMPORT_ERROR = None


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    NAME = "opsmill.infrahub.inventory"

    def verify_file(self, path: str) -> bool:
        """
        Check if the given file path is potentially valid for this plugin.

        The method first invokes the base class's `verify_file` method to ensure that the file
        exists and is readable by the current user. It then checks the file extension to see if
        it matches expected extensions (".yml" or ".yaml").

        Parameters:
            path (str): Path to the file to verify.

        Returns:
            bool: True if the file is potentially valid for this plugin, otherwise False.
        """
        if super(InventoryModule, self).verify_file(path):
            # Base class verifies that file exists and is readable by current user
            if path.endswith((".yml", ".yaml")):
                return True

        return False

    def _set_authorization(self):
        """
        Handle Infrahub API authentication
        """
        if version.parse(ansible_version) < version.parse("2.11"):
            self.token = self.get_option("token")
        else:
            self.templar.available_variables = self._vars
            self.token = self.templar.template(self.get_option("token"), fail_on_undefined=False)

    def _fetch_from_cache(self) -> Tuple[Optional[Dict], bool]:
        """
        Fetches data from the cache (if available)

        Returns:
        Tuple[Optional[Dict], bool]: A tuple containing two elements:
            1. A dictionary representing the host node attributes fetched from cache, or None if not available.
            2. A boolean indicating if there's a need to load data from the API. True indicates data should be fetched from the API.
        """

        if not self.use_cache:
            return None, True

        cache_key: str = self.get_cache_key(self.api_endpoint)

        if self.user_cache_setting and self.use_cache:
            self.display.v("Fetching cache.")
            try:
                host_node_attributes: Dict = json.loads(self._cache[cache_key])
                return host_node_attributes, not bool(host_node_attributes)
            except KeyError:
                self.display.v("Cache key not found. Need to load from API.")
                return None, True

        return None, True

    def _store_in_cache(self, host_node_attributes: Dict[str, Any]):
        """
        Store the host node attributes in the cache if the user cache setting is enabled.

        Parameters:
            host_node_attributes (Dict[str, Any]): Dictionary containing attributes for each host node.
        """

        if self.user_cache_setting:
            cache_key: str = self.get_cache_key(self.api_endpoint)
            self._cache[cache_key] = json.dumps(host_node_attributes)

    def set_hosts_and_groups(self, host_node_attributes: Dict[str, Any]):
        """
        Set host variables and add host to keyed groups based on the provided attributes.

        Parameters:
            host_node_attributes (Dict[str, Any]): Dictionary containing attributes for each host node.
        """

        for host_node, attributes in host_node_attributes.items():
            self.inventory.add_host(host_node)

            self.set_host_variables(host_node=host_node, attributes=attributes)

            self._add_host_to_keyed_groups(self.keyed_groups, attributes, host_node, strict=self.strict)

    def set_host_variables(self, host_node: str, attributes: Dict):
        """
        Set the variables for a particular host node.

        Parameters:
            host_node (str): The identifier or name of the host node for which the variables are being set.
            attributes (Dict): A dictionary representing attributes and their values to be associated with the host node.
        """

        for key, value in attributes.items():
            self.inventory.set_variable(host_node, key, value)

        self._set_composite_vars(self.compose, attributes, host_node, strict=self.strict)

    def main(self):
        """Main function"""
        if not HAS_INFRAHUBCLIENT:
            raise (AnsibleError("infrahub_sdk must be installed to use this plugin"))

        try:
            if not self.nodes:
                raise ValueError("node' is undefined.")
        except ValueError as exp:
            raise (AnsibleError(str(exp)))

        host_node_attributes, need_to_load_from_api = self._fetch_from_cache()

        if need_to_load_from_api:
            try:
                self.display.v("Initializing Infrahub Client")
                client = InfrahubclientWrapper(
                    api_endpoint=self.api_endpoint,
                    branch=self.branch,
                    token=self.token,
                    timeout=self.timeout,
                )
                processor = InfrahubNodesProcessor(client=client)
                self.display.v("Processing Nodes request")
                host_node_attributes = processor.fetch_and_process(nodes=self.nodes)
            except Exception as exp:
                raise_from(AnsibleError(str(exp)), exp)

        if not host_node_attributes:
            self.display.v("No nodes processed.")
        else:
            self.set_hosts_and_groups(host_node_attributes=host_node_attributes)
            self._store_in_cache(host_node_attributes=host_node_attributes)

    def parse(self, inventory, loader, path, cache=True):
        """
        Parse the inventory
        """
        super(InventoryModule, self).parse(inventory, loader, path)
        self._read_config_data(path=path)

        self.use_cache = cache
        self.user_cache_setting = self.get_option("cache")

        # Handle extra "/" from api_endpoint configuration and trim if necessary
        self.api_endpoint = self.get_option("api_endpoint").strip("/")
        self.validate_certs = self.get_option("validate_certs")
        self.timeout = self.get_option("timeout")

        self.branch = self.get_option("branch")
        self.nodes = self.get_option("nodes")

        self.strict = self.get_option("strict")
        self.compose = self.get_option("compose")
        self.keyed_groups = self.get_option("keyed_groups")

        self._set_authorization()

        self.main()
