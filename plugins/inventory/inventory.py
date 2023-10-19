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
                - token that ensures this is a source file for the 'infrahub.infrahub' plugin.
            required: True
            choices: ['infrahub.infrahub.inventory']
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
            description: Timeout for Nautobot requests in seconds
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
                    elements: list
                    suboptions:
                        filters:
                            description:
                                - List of filters to apply on the query for node_type.
                            type: list
                            default: []
                        include:
                            description:
                                - List of attributes to include for node_type.
                            type: list
                            default: []
                        exclude:
                            description:
                                - List of attributes to exclude for node_type.
                            type: list
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
plugin: infrahub.infrahub.inventory
api_endpoint: http://localhost:8000  # Can be omitted if the INFRAHUB_API environment variable is set
token: 1234567890123456478901234567  # Can be omitted if the INFRAHUB_TOKEN environment variable is set
"""

RETURN = """
  _list:
    description:
      - list of composed dictionaries with key and value
    type: list
"""
import json
from typing import Any, Dict, List, Optional

from ansible.errors import AnsibleError
from ansible.module_utils.ansible_release import __version__ as ansible_version
from ansible.module_utils.six import raise_from
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable

try:
    from infrahub_client import Config, InfrahubClientSync, InfrahubNodeSync, NodeSchema
    from infrahub_client.exceptions import (
        FilterNotFound,
        GraphQLError,
        SchemaNotFound,
        ServerNotReacheableError,
        ServerNotResponsiveError,
    )
    from infrahub_client.schema import RelationshipCardinality, RelationshipKind
except ImportError as imp_exc:
    INFRAHUBCLIENT_IMPORT_ERROR = imp_exc
else:
    INFRAHUBCLIENT_IMPORT_ERROR = None

try:
    from packaging import version
except ImportError as imp_exc:
    PACKAGING_IMPORT_ERROR = imp_exc
else:
    PACKAGING_IMPORT_ERROR = None


def resolve_node_mapping(
    node: InfrahubNodeSync, attrs: List[str], schemas: Dict[str, NodeSchema]
) -> Optional[Dict[str, Any]]:
    """
    Resolve the attributes and relationships of a given node based on a list of desired attributes.

    Parameters:
        node (InfrahubNodeSync): The node to which attributes/relationships are to be mapped.
        attrs (List[str]): A list of attribute names that should be fetched for the node.

    Returns:
        Dict[str, Any]: A dictionary mapping attribute/relationship names to their respective values.
                  For relationship with "many" cardinality, it will be a List (of related nodes)
    """
    attribute_dict = {}
    for attr in attrs:
        node_attr = getattr(node, attr)

        if attr in node._schema.attribute_names:
            if node_attr.value:
                attribute_dict[node_attr._schema.name] = str(node_attr.value)
            else:
                attribute_dict[node_attr._schema.name] = node_attr.value

        if attr in node._schema.relationship_names:
            # Workaround if peer are generics, we load the nodes inherited from it via fetch
            if not node_attr.schema.peer in schemas:
                node_attr.fetch()
            # Should we allow "recursive" depending of node_attr.schema.kind (generics or component)
            if node_attr.schema.cardinality == "many":
                peers: List[InfrahubNodeSync] = []
                for peer in node_attr:
                    if hasattr(peer.peer._schema, "attribute_names"):
                        peer_attribute = peer.peer._schema.attribute_names
                        peers.append(
                            resolve_node_mapping(
                                node=peer.peer, attrs=peer_attribute, schemas=schemas
                            )
                        )
                attribute_dict[node_attr.schema.name] = peers
            elif node_attr.schema.cardinality == "one":
                peer = node_attr.peer
                peer_attribute = peer._schema.attribute_names
                attribute_dict[node_attr.schema.name] = resolve_node_mapping(
                    node=peer, attrs=peer_attribute, schemas=schemas
                )

    return attribute_dict


def get_attributes_for_schema(
    schema: NodeSchema, exclude: Optional[List[str]] = None
) -> List[str]:
    """
    Build the attributes for the given kind.

    Parameters:
        schema (NodeSchema): The schema from which attributes/relationship are used
        exclude Optional[List[str]]: list of attributes/relationship to ignore

    Returns:
        List[str]: The schema attributes for the given kind.
    """
    exclude = exclude or []
    attributes_by_kind = []
    # From https://docs.infrahub.app/python-sdk/10_query/#control-what-will-be-queried
    #  "By default the query will include, the attributes, the relationships of cardinality one and the relationships of kind Attribute"
    for attr_name in schema.attribute_names:
        if exclude and attr_name in exclude:
            continue
        attributes_by_kind.append(attr_name)
    for rel_name in schema.relationship_names:
        if exclude and rel_name in exclude:
            continue
        rel_schema = schema.get_relationship(name=rel_name)
        if (
            rel_schema.cardinality == RelationshipCardinality.MANY  # type: ignore[union-attr]
            and rel_schema.kind not in [RelationshipKind.ATTRIBUTE, RelationshipKind.PARENT]  # type: ignore[union-attr]
        ):
            continue
        if rel_schema and rel_schema.cardinality == "one":
            attributes_by_kind.append(rel_name)
        elif rel_schema and rel_schema.cardinality == "many":
            attributes_by_kind.append(rel_name)
    return attributes_by_kind


def get_related_nodes(schema: NodeSchema, attrs: List[str]) -> List[str]:
    """
    Build a list of Node Kind base on the relationships of a given schema

    Parameters:
        schema (NodeSchema): The schema from which relationship are loaded
        attrs List[str]: list of attributes to compare to the schema

    Returns:
        List[str]: The node kind of the related nodes
    """
    relationship_schemas = [
        schema.peer for schema in schema.relationships if schema.name in attrs
    ]
    return list(set(relationship_schemas))


def build_include_from_constructed(compose: Dict, groups: List[Dict]) -> List[str]:
    """
    Build a List of str, based on the compose and keyed_groups options.

    Parameters:
        compose (Dict): A dictionary containing the compose options details.
        groups (List[Dict]): A list of dictionaries, each representing a group with specific attributes.

    Returns:
        List[str]: A list of strings constructed based on the input parameters.

    """
    include = []
    if compose:
        include_compose = [value.split(".")[0] for value in compose.values()]
        include += include_compose
    if groups:
        include_groups = [
            group["key"].split(".")[0] for group in groups if "key" in group
        ]
        include += include_groups
    return include


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    NAME = "infrahub.infrahub.inventory"

    def verify_file(self, path):
        """Return true/false if this is possibly a valid file for this plugin to consume."""
        if super(InventoryModule, self).verify_file(path):
            # Base class verifies that file exists and is readable by current user
            if path.endswith((".yml", ".yaml")):
                return True

        return False

    def fetch_nodes_by_kind(
        self,
        kind: str,
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        filters: Optional[List[str]] = None,
    ) -> List[InfrahubNodeSync]:
        """Retrieve all nodes of a given kind

        Parameters:
            kind (str): kind of the nodes to query
            include Optional[List[str]]: list of attributes/relationship to retrieve
            exclude Optional[List[str]]: list of attributes/relationship to ignore
            filters Optional[List[str]]: list of filters to apply on the query

        Returns:
            List[InfrahubNodeSync]: List of Nodes
        """
        try:
            if not filters:
                nodes = self.client.all(
                    kind=kind, populate_store=True, include=include, exclude=exclude
                )
            else:
                nodes = self.client.filters(
                    kind=kind,
                    include=include,
                    populate_store=True,
                    exclude=exclude,
                    **filters,
                )
            return nodes
        except GraphQLError:
            self.display.warning("Database not Responsive")
        except SchemaNotFound:
            pass  # until we are able to return Generics Schema and Core Schema https://github.com/opsmill/infrahub/issues/1217
        except FilterNotFound:
            self.display.warning(f"Filters {filters} not Found for {kind}")
        except ServerNotReacheableError:
            self.display.warning("Server not Reacheable")
        except ServerNotResponsiveError:
            self.display.warning("Server not Responsive")
        return None

    def fetch_schema_by_kind(self, kind: str) -> NodeSchema:
        """
        Retrieves schema attributes for the given kind.

        Parameters:
            kind (str): The kind for which the schema attributes are needed.
            exclude Optional[List[str]]: list of attributes/relationship to ignore

        Returns:
            List[str]: The schema attributes for the given kind.
        """
        try:
            schema = self.client.schema.get(kind=kind)
            return schema
        except GraphQLError:
            self.display.warning("Database not Responsive")
        except SchemaNotFound:
            pass  # until we are able to return Generics Schema and Core Schema https://github.com/opsmill/infrahub/issues/1217
        except ServerNotReacheableError:
            self.display.warning("Server not Reacheable")
        except ServerNotResponsiveError:
            self.display.warning("Server not Responsive")
        return None

    def set_host_variables(self, host_node: str, attributes: Dict):
        """
        Set the variables for a particular host node.

        Parameters:
            host_node (str): The identifier or name of the host node for which the variables are being set.
            attributes (Dict): A dictionary representing attributes and their values to be associated with the host node.
        """
        self.inventory.add_host(host_node)
        for key, value in attributes.items():
            self.inventory.set_variable(host_node, key, value)
        self._set_composite_vars(
            self.compose, attributes, host_node, strict=self.strict
        )

    def main(self):
        """Main function."""

        if INFRAHUBCLIENT_IMPORT_ERROR:
            raise_from(
                AnsibleError("infrahub_client must be installed to use this plugin"),
                INFRAHUBCLIENT_IMPORT_ERROR,
            )

        try:
            if not self.nodes:
                raise ValueError("Neither 'nodes' should be defined.")
        except ValueError as e:
            raise_from(AnsibleError(str(e)), e)

        if self.use_cache:
            cache_key = self.get_cache_key(self.api_endpoint)

        if self.user_cache_setting and self.use_cache:
            try:
                self.display.v("Fetching cache.")
                host_node_attributes = json.loads(self._cache[cache_key])
                need_to_load_from_api = False
            except KeyError:
                need_to_load_from_api = True
        else:
            need_to_load_from_api = True

        if need_to_load_from_api:
            self.display.vvvv("Initalizing InfrahubClientSync")
            self.client = InfrahubClientSync(
                address=self.api_endpoint,
                default_branch=self.branch,
                config=Config(api_token=self.token, timeout=self.timeout),
            )

            all_nodes = []
            self.schema_dict = {}
            node_attributes_dict = {}

            if self.nodes:
                self.display.v(f"Fetching API {self.api_endpoint} ")
                for node_kind in self.nodes:
                    self.display.vvv(
                        f"Fetching Schema for {node_kind} from API {self.api_endpoint}"
                    )
                    self.schema_dict[node_kind] = self.fetch_schema_by_kind(node_kind)
                    if self.nodes[node_kind]:
                        include = self.nodes[node_kind].get(
                            "include",
                            build_include_from_constructed(
                                compose=self.compose, groups=self.keyed_groups
                            ),
                        )
                        exclude = self.nodes[node_kind].get("exclude", None)
                        filters = self.nodes[node_kind].get("filters", None)
                    else:
                        include = build_include_from_constructed(
                            compose=self.compose, groups=self.keyed_groups
                        )
                        exclude = None
                        filters = None

                    self.display.vvv(f"Fetching Nodes for {node_kind}")
                    nodes_from_kind = self.fetch_nodes_by_kind(
                        node_kind,
                        include,
                        exclude,
                        filters,
                    )

                    if not nodes_from_kind:
                        continue
                    node_attributes_dict[node_kind] = (
                        include
                        if include
                        else get_attributes_for_schema(
                            self.schema_dict[node_kind], exclude
                        )
                    )
                    all_nodes.extend(nodes_from_kind)

            if not all_nodes:
                self.display.v("No nodes fetched.")
                return

            for node_kind, node_atributes in node_attributes_dict.items():
                related_kinds = get_related_nodes(
                    schema=self.schema_dict[node_kind], attrs=node_atributes
                )
                for related_kind in related_kinds:
                    self.schema_dict[node_kind] = self.fetch_schema_by_kind(
                        kind=related_kind
                    )
                    # fetching nodes to populate Store for related Nodes
                    self.fetch_nodes_by_kind(kind=related_kind)

            host_node_attributes = {}
            for host_node in all_nodes:
                result = resolve_node_mapping(
                    node=host_node,
                    attrs=node_attributes_dict[host_node._schema.kind],
                    schemas=self.schema_dict,
                )
                if result is not None:
                    host_node_attributes[str(host_node)] = result

        if self.user_cache_setting:
            self._cache[cache_key] = json.dumps(host_node_attributes)

        for host_node, attributes in host_node_attributes.items():
            self.set_host_variables(host_node, attributes)

            self._add_host_to_keyed_groups(
                self.keyed_groups, attributes, host_node, strict=self.strict
            )

    def _set_authorization(self):
        """Handle Infrahub API authentication."""
        if version.parse(ansible_version) < version.parse("2.11"):
            self.token = self.get_option("token")
        else:
            self.templar.available_variables = self._vars
            self.token = self.templar.template(
                self.get_option("token"), fail_on_undefined=False
            )

    def parse(self, inventory, loader, path, cache=True):
        """Parse the inventory."""
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
