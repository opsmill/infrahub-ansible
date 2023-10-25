from __future__ import absolute_import, division, print_function

__metaclass__ = type

import traceback
from typing import Any, Dict, List, Optional

from ansible_collections.infrahub.infrahub.plugins.module_utils.exception import (
    handle_infrahub_exceptions,
)

try:
    from infrahub_client import Config, InfrahubClientSync
    from infrahub_client.node import InfrahubNodeSync
    from infrahub_client.schema import (
        NodeSchema,
        RelationshipCardinality,
        RelationshipKind,
    )

    HAS_INFRAHUBCLIENT = True
    INFRAHUBCLIENT_IMP_ERR = None
except ImportError:
    INFRAHUBCLIENT_IMP_ERR = traceback.format_exc()
    HAS_INFRAHUBCLIENT = False

if not HAS_INFRAHUBCLIENT:

    class InfrahubClientSync:
        pass

    class InfrahubNodeSync:
        pass

    class NodeSchema:
        pass


def resolve_node_mapping(
    node: InfrahubNodeSync, attrs: List[str], schemas: Dict[str, NodeSchema]
) -> Optional[Dict[str, Any]]:
    """
    Resolve the attributes and relationships of a given node based on a list of desired attributes.

    Parameters:
        node (InfrahubNodeSync): The node to which attributes/relationships are to be mapped.
        attrs (List[str]): A list of attribute names that should be fetched for the node.
        schemas Dict[str, NodeSchema]: A dictionary of Node Kind name, NodeSchema

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
            elif node_attr.schema.peer in schemas:
                if not schemas[node_attr.schema.peer]:
                    node_attr.fetch()
            # Should we allow "recursive" depending of node_attr.schema.kind (generics or component)
            if node_attr.schema.cardinality == "many":
                peers: List[InfrahubNodeSync] = []
                for peer in node_attr:
                    if hasattr(peer.peer._schema, "attribute_names"):
                        peer_attribute = peer.peer._schema.attribute_names
                        peers.append(resolve_node_mapping(node=peer.peer, attrs=peer_attribute, schemas=schemas))
                attribute_dict[node_attr.schema.name] = peers
            elif node_attr.schema.cardinality == "one":
                peer = node_attr.peer
                peer_attribute = peer._schema.attribute_names
                attribute_dict[node_attr.schema.name] = resolve_node_mapping(
                    node=peer, attrs=peer_attribute, schemas=schemas
                )

    return attribute_dict


def get_attributes_for_schema(schema: NodeSchema, exclude: Optional[List[str]] = None) -> List[str]:
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
    relationship_schemas = [schema.peer for schema in schema.relationships if schema.name in attrs]
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
        include_groups = [group["key"].split(".")[0] for group in groups if "key" in group]
        include += include_groups
    return include


def initialize_infrahub_client(api_endpoint: str, branch: str, token: str, timeout: int) -> InfrahubClientSync:
    """
    Initializes and returns an instance of InfrahubClientSync.

    Parameters:
        api_endpoint (str): API endpoint for the Toto service.
        branch (str): Branch in which the request is made.
        token (str): Toto API token.
        timeout (int): Timeout for Toto requests in seconds.

    Returns:
        InfrahubClientSync: Initialized client instance.
    """
    return InfrahubClientSync(
        address=api_endpoint,
        default_branch=branch,
        config=Config(api_token=token, timeout=timeout),
    )


@handle_infrahub_exceptions
def fetch_nodes_by_kind(
    client: InfrahubClientSync,
    kind: str,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
    filters: Optional[Dict[str, str]] = None,
) -> List[InfrahubNodeSync]:
    """Retrieve all nodes of a given kind

    Parameters:
        client (InfrahubClientSync): The client object for Infrahub operations.
        kind (str): kind of the nodes to query
        include Optional[List[str]]: list of attributes/relationship to retrieve
        exclude Optional[List[str]]: list of attributes/relationship to ignore
        filters Optional[LiDictst[str]]: Dict of filters to apply on the query

    Returns:
        List[InfrahubNodeSync]: List of Nodes
    """
    nodes = List[InfrahubNodeSync]

    if not filters:
        nodes = client.all(kind=kind, populate_store=True, include=include, exclude=exclude)
    else:
        nodes = client.filters(
            kind=kind,
            include=include,
            populate_store=True,
            exclude=exclude,
            **filters,
        )
    return nodes


@handle_infrahub_exceptions
def fetch_schema_by_kind(client: InfrahubClientSync, kind: str) -> NodeSchema:
    """
    Retrieves schema attributes for the given kind.

    Parameters:
        client (InfrahubClientSync): The client object for Infrahub operations.
        kind (str): The kind for which the schema attributes are needed.

    Returns:
        NodeSchema: The schema attributes for the given kind.
    """
    return client.schema.get(kind=kind)


def fetch_and_process_nodes(client: InfrahubClientSync, nodes: List[str]) -> Optional[Dict[str, Any]]:
    """
    Fetches schemas and nodes for the given node kinds using the Infrahub client, then processes
    and maps these nodes to their corresponding attributes.

    Parameters:
        client (InfrahubClientSync): The client instance to interact with Infrahub API.
        nodes (List[str]): A list of node kinds to fetch and process.

    Returns:
        Optional[Dict[str, Any]]: A dictionary with processed host node attributes, or None if no nodes were processed.
    """
    all_nodes = []
    schema_dict = {}
    node_attributes_dict = {}

    if nodes:
        for node_kind in nodes:
            schema_dict[node_kind] = fetch_schema_by_kind(client, node_kind)
            node_options = nodes.get(node_kind, {})
            include = node_options.get("include", None)
            exclude = node_options.get("exclude", None)
            filters = node_options.get("filters", None)

            nodes_from_kind = fetch_nodes_by_kind(
                client=client,
                kind=node_kind,
                include=include,
                exclude=exclude,
                filters=filters,
            )

            if not nodes_from_kind:
                continue
            node_attributes_dict[node_kind] = (
                include if include else get_attributes_for_schema(schema_dict[node_kind], exclude)
            )
            all_nodes.extend(nodes_from_kind)

    if not all_nodes:
        return None

    host_node_attributes = {}
    for node_kind, node_attributes in node_attributes_dict.items():
        related_kinds = get_related_nodes(schema=schema_dict[node_kind], attrs=node_attributes)
        for related_kind in related_kinds:
            schema_dict[related_kind] = fetch_schema_by_kind(client, kind=related_kind)
            fetch_nodes_by_kind(client=client, kind=related_kind)

        for host_node in all_nodes:
            result = resolve_node_mapping(
                node=host_node,
                attrs=node_attributes_dict[host_node._schema.kind],
                schemas=schema_dict,
            )
            if result:
                host_node_attributes[str(host_node)] = result

    return host_node_attributes
