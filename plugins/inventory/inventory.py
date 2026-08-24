# Copyright (c) 2023 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = """
---
name: inventory
author:
    - Benoit Kohler (@bearchitek)
short_description: Infrahub inventory source (using GraphQL)
description:
    - Get inventory hosts from Infrahub.
    - When strict is false, a compose, groups or keyed_groups expression that fails to resolve
      emits one warning per expression naming the affected hosts, instead of failing silently.
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
          - name: INFRAHUB_ADDRESS
    token:
        required: True
        description:
          - Infrahub API token to be able to read against Infrahub.
        env:
          - name: INFRAHUB_API_TOKEN
    timeout:
        required: False
        description: Timeout for Infrahub requests in seconds
        type: int
        default: 10
    prefetch_relationships:
        required: False
        description: Prefetch relationships for Infrahub nodes
        type: bool
        default: True
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
          - List of custom Ansible host vars to create from the objects fetched from Infrahub
        type: dict
        default: {}
    keyed_groups:
        required: False
        description:
          - Create groups based on attributes or relationships.
          - groups is created as `attribute__value`
        type: list
        elements: str
        default: []
    groups:
        required: False
        description:
          - Create groups based on jinja filter.
        type: dict
        default: {}
    hostnames:
        required: False
        description:
          - A list of attribute paths used to determine the inventory hostname.
          - Each entry is a dotted path resolved against node attributes (e.g., "name", "primary_address.address").
          - The special value "display_label" resolves to the node's display label.
          - First non-empty string value wins. Falls back to display_label if none resolve.
          - Referenced attributes must be present in the node's include list.
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
api_endpoint: http://localhost:8000  # Can be omitted if the INFRAHUB_ADDRESS environment variable is set
token: 1234567890123456478901234567  # Can be omitted if the INFRAHUB_API_TOKEN environment variable is set

# Complete Example
# This will :
# - Retrieve in the branch "branch1" attributes for the Node Kind "InfraDevice"
# - The attributes wanted for "InfraDevice" are forced with the keyword "include"
# - Create 2 compose variable "hostname" ad "platform" (platform will override the attribute platform retrieved)
# - Create group based on the "site" name

strict: true

branch: "branch1"

nodes:
  InfraDevice:
    include:
      - name
      - platform.ansible_network_os
      - primary_address.address
      - site.name
      - interfaces

compose:
  hostname: name
  platform: platform.ansible_network_os

keyed_groups:
  - prefix: site
    key: site.name

# Using hostnames to set clean inventory hostnames
plugin: opsmill.infrahub.inventory
api_endpoint: http://localhost:8000

hostnames:
  - name
  - display_label

nodes:
  InfraDevice:
    include:
      - name
      - primary_address.address
"""

RETURN = """
  _list:
    description:
      - list of composed dictionaries with key and value
    type: list
"""
import json
import os
from functools import partial
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from ansible.errors import AnsibleError
from ansible.module_utils.ansible_release import __version__ as ansible_version
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import (
    HAS_INFRAHUBCLIENT,
    InfrahubclientWrapper,
    InfrahubNodesProcessor,
)

# Additional failing hosts listed by name in an aggregated strict:false warning.
MAX_LISTED_FAILURE_HOSTS = 5

PACKAGING_IMPORT_ERROR: ImportError | None = None

try:
    from packaging import version
except ImportError as imp_exc:
    PACKAGING_IMPORT_ERROR = imp_exc

try:
    from ansible.template import trust_as_template as _trust_as_template
except ImportError:  # ansible-core < 2.19

    def _trust_as_template(value: Any) -> Any:
        return value


def _mark_trusted(value: Any) -> Any:
    """Recursively mark string values as trusted-as-template.

    ansible-core 2.19's legacy JSON encoder wraps untagged strings as
    {"__ansible_unsafe": "..."} in `ansible-inventory --list` output;
    tagging plugin-supplied strings restores plain JSON output (#323).
    """
    if isinstance(value, str):
        return _trust_as_template(value)
    if isinstance(value, dict):
        return {k: _mark_trusted(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_mark_trusted(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_mark_trusted(v) for v in value)
    if isinstance(value, set):
        return {_mark_trusted(v) for v in value}
    return value


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
        # Base class verifies that file exists and is readable by current user
        return bool(super(InventoryModule, self).verify_file(path) and path.endswith((".yml", ".yaml")))  # noqa: UP008

    def _set_authorization(self) -> None:
        """
        Handle Infrahub API authentication
        """
        if version.parse(ansible_version) < version.parse("2.11"):
            self.token = self.get_option("token") or os.getenv("INFRAHUB_API_TOKEN")
        else:
            self.templar.available_variables = self._vars
            self.token = self.templar.template(self.get_option("token"), fail_on_undefined=False)

    def _fetch_from_cache(self) -> tuple[dict | None, bool]:
        """
        Fetches data from the cache (if available)

        Returns:
        tuple[Optional[dict], bool]: A tuple containing two elements:
            1. A dictionary representing the host node attributes fetched from cache, or None if not available.
            2. A boolean indicating if there's a need to load data from the API. True indicates data should be fetched from the API.
        """

        if not self.use_cache:
            return None, True

        cache_key: str = self.get_cache_key(self.api_endpoint)

        if self.user_cache_setting and self.use_cache:
            self.display.v("Fetching cache.")
            try:
                host_node_attributes: dict = json.loads(self._cache[cache_key])
                return host_node_attributes, not bool(host_node_attributes)
            except KeyError:
                self.display.v("Cache key not found. Need to load from API.")
                return None, True

        return None, True

    def _store_in_cache(self, host_node_attributes: dict[str, Any]) -> None:
        """
        Store the host node attributes in the cache if the user cache setting is enabled.

        Parameters:
            host_node_attributes (dict[str, Any]): dictionary containing attributes for each host node.
        """

        if self.user_cache_setting:
            cache_key: str = self.get_cache_key(self.api_endpoint)
            self._cache[cache_key] = json.dumps(host_node_attributes)

    def _apply_constructed_or_record(self, apply_entry: Callable[..., None], entry_key: str, host: str) -> None:
        """
        Apply a single constructed-inventory entry (compose / groups / keyed_groups),
        recording expression failures when strict mode is off.

        The Constructable helpers silently skip an entry whose expression fails to
        resolve under strict=False, which leaves group membership quietly incomplete
        (#385). Evaluate the entry strictly instead and record the failure for a
        per-expression warning; errors that strict=False would raise as well (invalid
        entry configuration) stay fatal.

        Parameters:
            apply_entry (Callable): applies one entry, accepting a `strict` keyword.
            entry_key (str): identity of the entry, used to aggregate failures across hosts.
            host (str): host the entry is being applied to.
        """
        try:
            apply_entry(strict=True)
        except AnsibleError as exc:
            apply_entry(strict=False)
            self._constructed_failures.setdefault(entry_key, []).append((host, str(exc)))

    def _warn_constructed_failures(self) -> None:
        """
        Emit one warning per failing expression instead of one per host, so a single
        broken expression on a large inventory does not flood the output. The first
        host's error is kept verbatim (it names the host and the expression) and the
        other affected hosts are listed.
        """
        for failures in self._constructed_failures.values():
            first_error = failures[0][1]
            if len(failures) == 1:
                self.display.warning(first_error)
                continue
            other_hosts = [host for host, _error in failures[1:]]
            listed = ", ".join(other_hosts[:MAX_LISTED_FAILURE_HOSTS])
            if len(other_hosts) > MAX_LISTED_FAILURE_HOSTS:
                listed += f", ... ({len(failures)} hosts affected in total)"
            self.display.warning(f"{first_error} (same failure for {len(other_hosts)} more host(s): {listed})")

    def set_hosts_and_groups(self, host_node_attributes: dict[str, Any]) -> None:
        """
        Set host variables and add host to keyed groups based on the provided attributes.

        Parameters:
            host_node_attributes (dict[str, Any]): dictionary containing attributes for each host node.
        """

        self._constructed_failures: dict[str, list[tuple[str, str]]] = {}

        for host_node, attributes in host_node_attributes.items():
            self.inventory.add_host(host_node)

            trusted_attributes = _mark_trusted(attributes)
            self.set_host_variables(host_node=host_node, attributes=trusted_attributes)

            if self.strict:
                self._add_host_to_composed_groups(
                    groups=self.groups,
                    variables=trusted_attributes,
                    host=host_node,
                    strict=True,
                )
                self._add_host_to_keyed_groups(
                    keys=self.keyed_groups,
                    variables=trusted_attributes,
                    host=host_node,
                    strict=True,
                )
            else:
                for group_name, expression in (self.groups or {}).items():
                    self._apply_constructed_or_record(
                        partial(
                            self._add_host_to_composed_groups,
                            groups={group_name: expression},
                            variables=trusted_attributes,
                            host=host_node,
                        ),
                        entry_key=f"groups:{group_name}",
                        host=host_node,
                    )
                for keyed_group in self.keyed_groups or []:
                    self._apply_constructed_or_record(
                        partial(
                            self._add_host_to_keyed_groups,
                            keys=[keyed_group],
                            variables=trusted_attributes,
                            host=host_node,
                        ),
                        entry_key=f"keyed_groups:{keyed_group}",
                        host=host_node,
                    )

        self._warn_constructed_failures()

    def set_host_variables(self, host_node: str, attributes: dict[str, Any]) -> None:
        """
        Set the variables for a particular host node.

        Parameters:
            host_node (str): The identifier or name of the host node for which the variables are being set.
            attributes (dict): A dictionary representing attributes and their values to be associated with the host node.
        """

        for key, value in attributes.items():
            self.inventory.set_variable(host_node, key, value)

        if self.strict:
            self._set_composite_vars(compose=self.compose, variables=attributes, host=host_node, strict=True)
        else:
            for varname, expression in (self.compose or {}).items():
                self._apply_constructed_or_record(
                    partial(
                        self._set_composite_vars,
                        compose={varname: expression},
                        variables=attributes,
                        host=host_node,
                    ),
                    entry_key=f"compose:{varname}",
                    host=host_node,
                )

    def main(self) -> None:
        """Main function"""
        if not HAS_INFRAHUBCLIENT:
            raise (AnsibleError("infrahub_sdk must be installed to use this plugin"))

        try:
            if not self.nodes:
                raise ValueError("node' is undefined.")
        except ValueError as exc:
            raise (AnsibleError(str(exc)))

        self.display.v("Initializing Infrahub Client")
        client = InfrahubclientWrapper(
            api_endpoint=self.api_endpoint,
            branch=self.branch,
            token=self.token,
            timeout=self.timeout,
            validate_certs=self.validate_certs,
            display=self.display,
        )
        processor = InfrahubNodesProcessor(client=client, display=self.display)

        host_node_attributes, need_to_load_from_api = self._fetch_from_cache()

        if need_to_load_from_api:
            try:
                self.display.v("Processing Nodes request")
                host_node_attributes = processor.fetch_and_process(
                    nodes=self.nodes, prefetch_relationships=self.prefetch_relationships
                )
            except Exception as exc:
                raise AnsibleError(str(exc)) from exc

        if not host_node_attributes:
            self.display.v("No nodes processed.")
        else:
            # Store raw (pre-resolution) data in cache so hostname config
            # changes are always applied on next load.
            self._store_in_cache(host_node_attributes=host_node_attributes)
            host_node_attributes = processor.resolve_hostnames(host_node_attributes, self.hostnames)
            self.set_hosts_and_groups(host_node_attributes=host_node_attributes)

    def parse(self, inventory: Any, loader: Any, path: Any, cache: bool = True) -> None:
        """
        Parse the inventory
        """
        super(InventoryModule, self).parse(inventory=inventory, loader=loader, path=path, cache=cache)  # noqa: UP008
        self._read_config_data(path=path)

        self.use_cache = cache
        self.user_cache_setting = self.get_option("cache")

        # Handle extra "/" from api_endpoint configuration and trim if necessary
        self.api_endpoint = self.get_option("api_endpoint").strip("/")
        self.validate_certs = self.get_option("validate_certs")

        self.api_endpoint = self.get_option("api_endpoint") or os.getenv("INFRAHUB_ADDRESS")
        if self.api_endpoint is None:
            raise AnsibleError("Missing Infrahub API Endpoint.")

        self.api_endpoint = self.api_endpoint.strip("/")
        self.timeout = self.get_option("timeout")
        self.prefetch_relationships = self.get_option("prefetch_relationships", True)
        self.validate_certs = self.get_option("validate_certs", True)
        self.branch = self.get_option("branch")
        self.nodes = self.get_option("nodes")

        self.strict = self.get_option("strict")
        self.compose = self.get_option("compose")
        self.keyed_groups = self.get_option("keyed_groups")
        self.groups = self.get_option("groups")
        self.hostnames = self.get_option("hostnames") or []

        self._set_authorization()
        if self.token is None:
            raise AnsibleError("Missing Infrahub Token.")

        self.main()
