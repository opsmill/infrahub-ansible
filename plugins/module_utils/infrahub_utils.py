from __future__ import absolute_import, division, print_function

__metaclass__ = type

import traceback
from typing import Any, Dict, List, Optional, Union

from ansible_collections.opsmill.infrahub.plugins.module_utils.exception import (
    handle_infrahub_exceptions,
)

try:
    from infrahub_sdk import Config, InfrahubClientSync
    from infrahub_sdk.branch import BranchData, InfrahubBranchManagerSync
    from infrahub_sdk.graphql import Query
    from infrahub_sdk.node import InfrahubNodeSync
    from infrahub_sdk.schema import (
        NodeSchema,
        RelationshipCardinality,
        RelationshipKind,
    )

    HAS_INFRAHUBCLIENT = True
    INFRAHUBCLIENT_IMP_ERR = None
except ImportError:
    INFRAHUBCLIENT_IMP_ERR = traceback.format_exc()
    HAS_INFRAHUBCLIENT = False
else:
    HAS_INFRAHUBCLIENT = True

if HAS_INFRAHUBCLIENT:
    TYPE_MAPPING = {"str": str, "int": int, "float": float, "bool": bool}

    class InfrahubclientWrapper:
        def __init__(self, api_endpoint: str, branch: str, token: str, timeout: Optional[int] = 10):
            """
            Initializes InfrahubclientWrapper.

            Parameters:
                api_endpoint (str): API endpoint for the Toto service.
                branch (str): Branch in which the request is made.
                token (str): Toto API token.
                timeout (int): Timeout for Toto requests in seconds.
            """
            self.client = InfrahubClientSync(
                address=api_endpoint,
                default_branch=branch,
                config=Config(api_token=token, timeout=timeout),
            )
            self.branch_manager = InfrahubBranchManagerSync(self.client)

        @handle_infrahub_exceptions
        def fetch_nodes(
            self,
            kind: str,
            include: Optional[List[str]] = None,
            exclude: Optional[List[str]] = None,
            filters: Optional[Dict[str, str]] = None,
            branch: Optional[str] = None,
        ) -> List[InfrahubNodeSync]:
            """
            Retrieve all nodes of a given kind

            Parameters:
                kind (str): kind of the nodes to query
                include (Optional[List[str]]): list of attributes/relationship to retrieve
                exclude (Optional[List[str]]): list of attributes/relationship to ignore
                filters (Optional[Dict[str, str]]): Dict of filters to apply on the query
                branch (Optional[str]): Name of the branch to query from. Defaults to default_branch.

            Returns:
                List[InfrahubNodeSync]: List of Nodes
            """
            nodes = List[InfrahubNodeSync]

            if not filters:
                nodes = self.client.all(kind=kind, populate_store=True, include=include, exclude=exclude, branch=branch)
            else:
                nodes = self.client.filters(
                    kind=kind,
                    include=include,
                    populate_store=True,
                    exclude=exclude,
                    branch=branch,
                    **filters,
                )
            return nodes

        @handle_infrahub_exceptions
        def fetch_single_schema(self, kind: str, branch: Optional[str] = None) -> NodeSchema:
            """
            Retrieves schema attributes for the given kind.

            Parameters:
                kind (str): The kind for which the schema attributes are needed.
                branch (Optional[str]): Name of the branch to query from. Defaults to default_branch.

            Returns:
                NodeSchema: The schema attributes for the given kind.
            """
            return self.client.schema.get(kind=kind, branch=branch)

        @handle_infrahub_exceptions
        def fetch_schemas(self, branch: Optional[str] = None) -> Dict[str, NodeSchema]:
            """
            Retrieves schema attributes for the given kind.

            Parameters:
                branch (Optional[str]): Name of the branch to query from. Defaults to default_branch.

            Returns:
                Dict[str, NodeSchema]:: A Dict of node kind, Schema.
            """
            branch = branch or self.default_branch
            return self.client.schema.get(branch=branch)

        @handle_infrahub_exceptions
        def fetch_branchs(self) -> Dict[str, BranchData]:
            """
            Retrieves all available branches.

            Returns:
                Dict[str, BranchData]: A dictionary containing all branches.
            """
            return self.branch_manager.all()

        @handle_infrahub_exceptions
        def fetch_branch(self, branch_name: str) -> BranchData:
            """
            Retrieves details of a specific branch.

            Parameters:
                branch_name (str): The name of the branch to be fetched.

            Returns:
                BranchData: Details of the specified branch.
            """
            return self.branch_manager.get(branch_name=branch_name)

        def _render_query(self, query: Dict, variables: Optional[Dict] = None) -> str:
            """
            Render a Grapql Query from a Dict to a String

            Parameters:
                query (Dict): GraphQL Query to render, can be a query or a mutation
                variables (Optional[Dict]): Variables to pass along with the GraphQL query. Defaults to None.

            Returns:
                Str: Graphql Query rendered as a string
            """
            if variables:
                variables_type = {}
                for key, value in variables.items():
                    variables_type[key] = type(value)
                query_str = Query(query=query, variables=variables_type).render()
            else:
                query_str = Query(query=query).render()
            return query_str

        @handle_infrahub_exceptions
        def execute_graphql(
            self, query: str, variables: Optional[Dict[str, Any]] = None, branch: Optional[str] = None
        ) -> Dict:
            """
            Executes a GraphQL query against the Infrahub Endpoint.

            Parameters:
                query (str): The GraphQL query string to execute.
                variables (Optional[Dict]): Variables to pass along with the GraphQL query. Defaults to None.
                branch (Optional[str]): Name of the branch to query from. Defaults to default_branch.

            Returns:
                Dict: The result of the executed GraphQL query.
            """
            # TODO :  Do something wit the variables ?
            response = self.client.execute_graphql(query=query, variables=variables, branch_name=branch)
            return response

    class InfrahubBaseProcessor:
        def __init__(self, client: InfrahubclientWrapper):
            self.client = client

        def resolve_node_mapping(
            self, node: InfrahubNodeSync, attrs: List[str], schemas: Dict[str, NodeSchema]
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
                    if node_attr.schema.peer not in schemas:
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
                                peers.append(
                                    self.resolve_node_mapping(node=peer.peer, attrs=peer_attribute, schemas=schemas)
                                )
                        attribute_dict[node_attr.schema.name] = peers
                    elif node_attr.schema.cardinality == "one":
                        peer = node_attr.peer
                        peer_attribute = peer._schema.attribute_names
                        attribute_dict[node_attr.schema.name] = self.resolve_node_mapping(
                            node=peer, attrs=peer_attribute, schemas=schemas
                        )

            return attribute_dict

    class InfrahubNodesProcessor(InfrahubBaseProcessor):
        @staticmethod
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

        @staticmethod
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

        @staticmethod
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

        def fetch_and_process(self, nodes: List[str]) -> Optional[Dict[str, Any]]:
            """
            Fetches schemas and nodes for the given node kinds using the Infrahub client wrapper,
            then processes and maps these nodes to their corresponding attributes.

            Parameters:
                nodes (List[str]): A list of node kinds to fetch and process.

            Returns:
                Optional[Dict[str, Any]]: A dictionary with processed host node attributes, or None if no nodes were processed.
            """
            all_nodes: List[InfrahubNodeSync] = []
            schema_dict = {}
            node_attributes_dict = {}

            if not nodes:
                return None
            for node_kind in nodes:
                schema_dict[node_kind] = self.client.fetch_single_schema(kind=node_kind)
                node_options = nodes.get(node_kind, {})
                if node_options:
                    include = node_options.get("include", None)
                    exclude = node_options.get("exclude", None)
                    filters = node_options.get("filters", None)
                else:
                    include = None
                    exclude = None
                    filters = None

                nodes_from_kind = self.client.fetch_nodes(
                    kind=node_kind,
                    include=include,
                    exclude=exclude,
                    filters=filters,
                )

                if not nodes_from_kind:
                    continue
                node_attributes_dict[node_kind] = (
                    include if include else self.get_attributes_for_schema(schema_dict[node_kind], exclude)
                )
                all_nodes.extend(nodes_from_kind)

            if not all_nodes:
                return None

            host_node_attributes = {}
            for node_kind, node_attributes in node_attributes_dict.items():
                related_kinds = self.get_related_nodes(schema=schema_dict[node_kind], attrs=node_attributes)
                for related_kind in related_kinds:
                    schema_dict[related_kind] = self.client.fetch_single_schema(kind=related_kind)
                    self.client.fetch_nodes(kind=related_kind)

                for host_node in all_nodes:
                    result = self.resolve_node_mapping(
                        node=host_node,
                        attrs=node_attributes_dict[host_node._schema.kind],
                        schemas=schema_dict,
                    )
                    if result:
                        result["id"] = host_node.id
                        host_node_attributes[str(host_node)] = result

            return host_node_attributes

    class InfrahubQueryProcessor(InfrahubBaseProcessor):
        def fetch_and_process(
            self, query: Union[dict, str], variables: Optional[Dict[str, Any]] = None
        ) -> Optional[Dict[str, Any]]:
            """
            Fetches nodes for the given GraphQl query using the Infrahub client wrapper,
            then processes and maps these nodes to their corresponding attributes.

            Parameters:
                query (str): A GraphQL formatted query string
                variables (Optional[Dict[str, Any]]): A dictionaries of variables to use with the query

            Returns:
                Optional[Dict[str, Any]]: A dictionary with processed host node attributes, or None if no nodes were processed.
            """
            if not query:
                return None

            results = []
            if isinstance(query, Dict):
                query_str = self.client._render_query(query=query, variables=variables)
            elif isinstance(query, str):
                if variables:
                    # TODO Need a rendering
                    raise Exception("query need to be a dict if your are using variables")
                else:
                    query_str = query
            else:
                raise Exception("query is neither a string nor a Dict")

            response = self.client.execute_graphql(query=query_str, variables=variables)
            for kind in response:
                if response[kind]["edges"]:
                    results += response[kind]["edges"]
            return results


if not HAS_INFRAHUBCLIENT:

    class InfrahubclientWrapper:
        pass

    class InfrahubclientWrapper:
        pass

    class InfrahubNodesProcessor:
        pass

    class InfrahubQueryProcessor:
        pass
