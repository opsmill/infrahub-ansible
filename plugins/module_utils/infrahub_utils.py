from __future__ import annotations

import traceback
from typing import Any

from ansible_collections.opsmill.infrahub.plugins.module_utils.exception import (
    handle_infrahub_exceptions,
)
from infrahub_sdk.types import Order

try:
    from infrahub_sdk import Config, InfrahubClientSync
    from infrahub_sdk.branch import BranchData, InfrahubBranchManagerSync
    from infrahub_sdk.graphql import Query
    from infrahub_sdk.node import InfrahubNodeSync, RelatedNodeSync, RelationshipManagerSync
    from infrahub_sdk.schema import (
        GenericSchemaAPI,
        NodeSchemaAPI,
        ProfileSchemaAPI,
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
        def __init__(
            self,
            api_endpoint: str,
            branch: str,
            token: str,
            timeout: int | None = 10,
            validate_certs: str | None = True,
        ):
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
                config=Config(api_token=token, timeout=timeout, default_branch=branch, tls_insecure=not validate_certs),
            )
            self.branch_manager = InfrahubBranchManagerSync(self.client)

        @handle_infrahub_exceptions
        def fetch_single_artifact(
            self,
            filters: dict[str, str],
            branch: str | None = None,
        ) -> list[InfrahubNodeSync]:
            """
            Retrieve all artifact content

            Parameters:
                artifact (dict[str, str], optional): dict of filters to apply on the query
                branch (str, optional): Name of the branch to query from. Defaults to default_branch.

            Returns:
                dict: Artifact Content
            """
            result = {
                "json": None,
                "text": None,
            }
            node = self.fetch_single_node(
                kind="CoreArtifact",
                filters=filters,
                branch=branch,
            )
            resp = self.client._get(url=f"{self.client.address}/api/storage/object/{node.storage_id.value}")
            if node.content_type.value == "application/json":
                result["json"] = resp.json()
            else:
                result["text"] = resp.text

            return result

        @handle_infrahub_exceptions
        def fetch_artifacts(
            self,
            filters: dict[str, str] | None = None,
            branch: str | None = None,
        ) -> list[InfrahubNodeSync]:
            """
            Retrieve all artifact content

            Parameters:
                filters (dict[str, str], optional): dict of filters to apply on the query
                branch (str, optional): Name of the branch to query from. Defaults to default_branch.

            Returns:
                list[dict]: list of Artifact Content
            """
            result = {
                "json": None,
                "text": None,
            }
            order = Order(disable=True)
            results = list[result]
            nodes = self.fetch_nodes(
                kind="CoreArtifact",
                filters=filters,
                branch=branch,
                orde=order,
            )
            for node in nodes:
                resp = self.client._get(url=f"{self.client.address}/api/storage/object/{node.storage_id.value}")

                if node.value == "application/json":
                    result["json"] = resp.json()
                else:
                    result["text"] = resp.text

                results.append(result)
            return results

        @handle_infrahub_exceptions
        def fetch_single_node(  # noqa: PLR0917
            self,
            kind: str,
            id: str | None = None,
            hfid: list[str] | None = None,
            include: list[str] | None = None,
            exclude: list[str] | None = None,
            filters: dict[str, str] | None = None,
            branch: str | None = None,
            prefetch_relationships: bool | None = True,
        ) -> InfrahubNodeSync:
            """
            Retrieve a single node of a given kind based on filters

            Parameters:
                kind (str): kind of the nodes to query
                id (str, optional): ID of the node to retrieve
                hfid (list[str], optional): HFID of the node to retrieve
                include (list[str], optional): list of attributes/relationship to retrieve
                exclude (list[str], optional): list of attributes/relationship to ignore
                filters (dict[str, str], optional): dict of filters to apply on the query
                branch (str, optional): Name of the branch to query from. Defaults to default_branch.
                prefetch_relationships (bool, optional): Whether to prefetch relationships when fetching nodes. Defaults to True.

            Returns:
                InfrahubNodeSync: Single Infrahub Node
            """
            if id:
                filters["ids"] = [id]
            if hfid:
                filters["hfid"] = hfid

            if not filters:
                raise Exception("At least one filter must be provided")

            node = self.client.get(
                kind=kind,
                id=id,
                hfid=hfid,
                include=include,
                populate_store=True,
                exclude=exclude,
                branch=branch,
                prefetch_relationships=prefetch_relationships,
                **filters,
            )
            return node

        @handle_infrahub_exceptions
        def fetch_nodes(  # noqa: PLR0917
            self,
            kind: str,
            include: list[str] | None = None,
            exclude: list[str] | None = None,
            filters: dict[str, str] | None = None,
            branch: str | None = None,
            prefetch_relationships: bool | None = True,
            order: Order | None = None,
        ) -> list[InfrahubNodeSync]:
            """
            Retrieve all nodes of a given kind

            Parameters:
                kind (str): kind of the nodes to query
                include (list[str], optional): list of attributes/relationship to retrieve
                exclude (list[str], optional): list of attributes/relationship to ignore
                filters (dict[str, str], optional): dict of filters to apply on the query
                branch (str, optional): Name of the branch to query from. Defaults to default_branch.
                prefetch_relationships (bool, optional): Whether to prefetch relationships when fetching nodes. Defaults to True.
                order (Order, optional): Ordering related options. Setting disable=True enhances performances.
            Returns:
                list[InfrahubNodeSync]: list of Nodes
            """
            nodes = list[InfrahubNodeSync]

            if not filters:
                nodes = self.client.all(
                    kind=kind,
                    populate_store=True,
                    include=include,
                    exclude=exclude,
                    branch=branch,
                    prefetch_relationships=prefetch_relationships,
                    parallel=True,
                    property=False,
                    order=order,
                )
            else:
                nodes = self.client.filters(
                    kind=kind,
                    include=include,
                    populate_store=True,
                    exclude=exclude,
                    branch=branch,
                    prefetch_relationships=prefetch_relationships,
                    parallel=True,
                    property=False,
                    order=order,
                    **filters,
                )
            return nodes

        @handle_infrahub_exceptions
        def fetch_single_schema(
            self, kind: str, branch: str | None = None
        ) -> NodeSchemaAPI | GenericSchemaAPI | ProfileSchemaAPI:
            """
            Retrieves schema attributes for the given kind.

            Parameters:
                kind (str): The kind for which the schema attributes are needed.
                branch (str, optional): Name of the branch to query from. Defaults to default_branch.

            Returns:
                NodeSchemaAPI | GenericSchemaAPI | ProfileSchemaAPI: The schema attributes for the given kind.
            """
            return self.client.schema.get(kind=kind, branch=branch)

        @handle_infrahub_exceptions
        def fetch_schemas(
            self, branch: str | None = None
        ) -> dict[str, NodeSchemaAPI | GenericSchemaAPI | ProfileSchemaAPI] | None:
            """
            Retrieves schema attributes for the given kind.

            Parameters:
                branch (str, optional): Name of the branch to query from. Defaults to default_branch.

            Returns:
                dict[str, NodeSchemaAPI | GenericSchemaAPI | ProfileSchemaAPI]:: A dict of node kind, Schema.
            """
            branch = branch or self.default_branch
            return self.client.schema.get(branch=branch)

        @handle_infrahub_exceptions
        def fetch_branchs(self) -> dict[str, BranchData]:
            """
            Retrieves all available branches.

            Returns:
                dict[str, BranchData]: A dictionary containing all branches.
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

        def _render_query(self, query: dict, variables: dict | None = None) -> str:
            """
            Render a Grapql Query from a dict to a String

            Parameters:
                query (dict): GraphQL Query to render, can be a query or a mutation
                variables (dict | None): Variables to pass along with the GraphQL query. Defaults to None.

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
            self, query: str, variables: dict[str, Any] | None = None, branch: str | None = None
        ) -> dict:
            """
            Executes a GraphQL query against the Infrahub Endpoint.

            Parameters:
                query (str): The GraphQL query string to execute.
                variables (dict | None): Variables to pass along with the GraphQL query. Defaults to None.
                branch (str, optional): Name of the branch to query from. Defaults to default_branch.

            Returns:
                dict: The result of the executed GraphQL query.
            """
            # TODO :  Do something wit the variables ?
            response = self.client.execute_graphql(query=query, variables=variables, branch_name=branch)
            return response

    class InfrahubBaseProcessor:
        def __init__(self, client: InfrahubclientWrapper):
            self.client = client

        def resolve_node_mapping(
            self, node: InfrahubNodeSync, attrs: list[str], schemas: dict[str, Any], include_id: bool = True
        ) -> dict[str, Any] | None:
            """
            Resolve the attributes and relationships of a given node based on a list of desired attributes.

            Parameters:
                node (InfrahubNodeSync): The node to which attributes/relationships are to be mapped.
                attrs (list[str]): A list of attribute names that should be fetched for the node.
                schemas dict[str, Any]: A dictionary of Node Kind name, Any
                include_id (bool): Whether to include the node ID in the result. Defaults to True.

            Returns:
                dict[str, Any]: A dictionary mapping attribute/relationship names to their respective values.
                        For relationship with "many" cardinality, it will be a list (of related nodes)
            """
            attribute_dict = {}
            store = self.client.client.store

            for attr in attrs:
                parts = attr.split(".")
                node_attr = getattr(node, parts[0], None)

                if parts[0] not in attribute_dict:
                    attribute_dict[parts[0]] = {} if len(parts) > 1 else None

                if node_attr is None:
                    continue

                if parts[0] in node._schema.attribute_names and len(parts) == 1:
                    if node_attr.value:
                        attribute_dict[parts[0]] = str(node_attr.value)
                    else:
                        # attribute_dict[parts[0]] = node_attr.value
                        # FIXME
                        # If the attribute is inherited, it's not populate properly in store
                        tmp_node = node._client.get(id=node.id, kind=node._schema.kind)
                        node_attr = getattr(tmp_node, parts[0], None)
                        if node_attr.value:
                            attribute_dict[parts[0]] = str(node_attr.value)
                        else:
                            attribute_dict[parts[0]] = node_attr.value

                elif parts[0] in node._schema.relationship_names:
                    if isinstance(node_attr, RelationshipManagerSync) and len(parts) == 1:
                        peers: list[dict[str, Any]] = []
                        for peer in node_attr.peers:
                            related_node = store.get(key=peer.id, raise_when_missing=False)
                            if not related_node:
                                peer.fetch()
                                related_node = peer.peer
                            if related_node and hasattr(related_node._schema, "attribute_names"):
                                peers.append(related_node.id)
                        attribute_dict[parts[0]] = peers

                    elif isinstance(node_attr, RelatedNodeSync):
                        if node_attr.id and node_attr.schema.peer:
                            related_node = store.get(key=node_attr.id, raise_when_missing=False)
                            if not related_node:
                                node_attr.fetch()
                                related_node = node_attr.peer
                            if related_node:
                                if len(parts) == 1:
                                    attribute_dict[parts[0]] = related_node.id
                                else:
                                    peer_attributes = [".".join(parts[1:])]
                                    nested_result = self.resolve_node_mapping(
                                        node=related_node, attrs=peer_attributes, schemas=schemas, include_id=True
                                    )
                                    if isinstance(attribute_dict[parts[0]], dict):
                                        attribute_dict[parts[0]].update(nested_result)
                                    else:
                                        attribute_dict[parts[0]] = nested_result

            if include_id:
                attribute_dict["id"] = node.id

            return attribute_dict

    class InfrahubNodesProcessor(InfrahubBaseProcessor):
        @staticmethod
        def get_attributes_for_schema(
            schema: NodeSchemaAPI | GenericSchemaAPI | ProfileSchemaAPI, exclude: list[str] | None = None
        ) -> list[str] | None:
            """
            Build the attributes for the given kind.

            Parameters:
                schema (NodeSchemaAPI | GenericSchemaAPI | ProfileSchemaAPI): The schema from which attributes/relationship are used
                exclude list[str] | None: list of attributes/relationship to ignore

            Returns:
                list[str]: The schema attributes for the given kind.
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
                rel_schema = schema.get_relationship_or_none(name=rel_name)
                if not rel_schema:
                    continue
                if (
                    rel_schema.cardinality == RelationshipCardinality.MANY  # type: ignore[union-attr]
                    and rel_schema.kind not in [RelationshipKind.ATTRIBUTE, RelationshipKind.PARENT]  # type: ignore[union-attr]
                ):
                    continue
                if rel_schema and rel_schema.cardinality in (RelationshipCardinality.ONE, RelationshipCardinality.MANY):
                    attributes_by_kind.append(rel_name)
            return attributes_by_kind

        @staticmethod
        def get_related_nodes(
            schema: NodeSchemaAPI | GenericSchemaAPI | ProfileSchemaAPI, attrs: list[str]
        ) -> list[str]:
            """
            Build a list of Node Kind base on the relationships of a given schema

            Parameters:
                schema (NodeSchemaAPI | GenericSchemaAPI | ProfileSchemaAPI): The schema from which relationship are loaded
                attrs list[str]: list of attributes to compare to the schema

            Returns:
                list[str]: The node kind of the related nodes
            """
            relationship_schemas = [schema.peer for schema in schema.relationships if schema.name in attrs]
            return list(set(relationship_schemas))

        @staticmethod
        def build_include_from_constructed(compose: dict, groups: list[dict]) -> list[str]:
            """
            Build a list of str, based on the compose and keyed_groups options.

            Parameters:
                compose (dict): A dictionary containing the compose options details.
                groups (list[dict]): A list of dictionaries, each representing a group with specific attributes.

            Returns:
                list[str]: A list of strings constructed based on the input parameters.

            """
            include = []
            if compose:
                include_compose = [value.split(".")[0] for value in compose.values()]
                include += include_compose
            if groups:
                include_groups = [group["key"].split(".")[0] for group in groups if "key" in group]
                include += include_groups
            return include

        def fetch_and_process(
            self,
            nodes: dict[str, Any],
            prefetch_relationships: bool | None = True,
            include_id: bool = True,
        ) -> dict[str, Any] | None:
            """
            Fetches schemas and nodes for the given node kinds using the Infrahub client wrapper,
            then processes and maps these nodes to their corresponding attributes.

            Parameters:
                nodes (dict[str, Any]): A dictionary of node kinds to fetch and process.
                prefetch_relationships (bool, optional): Whether to prefetch relationships when fetching nodes. Defaults to True.
                include_id (bool): Whether to include the node ID in the result. Defaults to True.

            Returns:
                dict[str, Any] | None: A dictionary with processed host node attributes, or None if no nodes were processed.
            """
            all_nodes: list[InfrahubNodeSync] = []
            schema_dict = {}
            node_attributes_dict = {}
            order = Order(disable=True)

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
                    prefetch_relationships=prefetch_relationships,
                    order=order,
                )

                if not nodes_from_kind:
                    continue
                node_attributes_dict[node_kind] = include or self.get_attributes_for_schema(
                    schema=schema_dict[node_kind], exclude=exclude
                )
                all_nodes.extend(nodes_from_kind)

            if not all_nodes:
                return None

            host_node_attributes = {}
            for node_kind, node_attributes in node_attributes_dict.items():
                related_kinds = self.get_related_nodes(schema=schema_dict[node_kind], attrs=node_attributes)
                for related_kind in related_kinds:
                    schema_dict[related_kind] = self.client.fetch_single_schema(kind=related_kind)
                    self.client.fetch_nodes(kind=related_kind, prefetch_relationships=False, order=order)
                for host_node in all_nodes:
                    result = self.resolve_node_mapping(
                        node=host_node,
                        attrs=node_attributes_dict[host_node._schema.kind],
                        schemas=schema_dict,
                        include_id=include_id,
                    )
                    if result:
                        host_node_attributes[str(host_node)] = result

            return host_node_attributes

    class InfrahubQueryProcessor(InfrahubBaseProcessor):
        def fetch_and_process(
            self,
            query: dict | str,
            variables: dict[str, Any] | None = None,
            include_id: bool = True,  # noqa: ARG002
        ) -> dict[str, Any] | None:
            """
            Fetches nodes for the given GraphQl query using the Infrahub client wrapper,
            then processes and maps these nodes to their corresponding attributes.

            Parameters:
                query (str): A GraphQL formatted query string
                variables (dict[str, Any] | None): A dictionaries of variables to use with the query
                include_id (bool): Whether to include the node ID in the result. Defaults to True.

            Returns:
                dict[str, Any] | None: A dictionary with processed host node attributes, or None if no nodes were processed.
            """
            if not query:
                return None

            results = []
            if isinstance(query, dict):
                query_str = self.client._render_query(query=query, variables=variables)
            elif isinstance(query, str):
                if variables:
                    # TODO Need a rendering
                    raise Exception("query need to be a dict if your are using variables")
                query_str = query
            else:
                raise Exception("query is neither a string nor a dict")

            response = self.client.execute_graphql(query=query_str, variables=variables)
            for kind in response:
                if response[kind]["edges"]:
                    results += response[kind]["edges"]
            return results


if not HAS_INFRAHUBCLIENT:

    class InfrahubclientWrapper:
        pass

    class InfrahubNodesProcessor:
        pass

    class InfrahubQueryProcessor:
        pass
