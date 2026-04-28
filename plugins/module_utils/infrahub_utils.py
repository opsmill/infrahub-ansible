from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

import traceback
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from ansible.module_utils.basic import env_fallback
from ansible_collections.opsmill.infrahub.plugins.module_utils.exception import handle_infrahub_exceptions_decorator

if TYPE_CHECKING:
    from ansible.module_utils.basic import AnsibleModule, Display
    from infrahub_sdk.branch import BranchData

try:
    from infrahub_sdk import Config, InfrahubClientSync
    from infrahub_sdk.exceptions import BranchNotFoundError, SchemaNotFoundError
    from infrahub_sdk.graphql import Query
    from infrahub_sdk.node import (
        InfrahubNodeSync,
        RelatedNodeSync,
        RelationshipManagerSync,
    )
    from infrahub_sdk.schema import (
        GenericSchemaAPI,
        NodeSchemaAPI,
        ProfileSchemaAPI,
        RelationshipCardinality,
        RelationshipKind,
    )
    from infrahub_sdk.types import Order
    from infrahub_sdk.utils import dict_hash, is_valid_uuid

    HAS_INFRAHUBCLIENT = True
    INFRAHUBCLIENT_IMP_ERR = None
except ImportError:
    INFRAHUBCLIENT_IMP_ERR = traceback.format_exc()
    HAS_INFRAHUBCLIENT = False
else:
    HAS_INFRAHUBCLIENT = True

INFRAHUB_ARG_SPEC = dict(
    api_endpoint=dict(type="str", required=False, fallback=(env_fallback, ["INFRAHUB_ADDRESS"])),
    token=dict(type="str", required=False, no_log=True, fallback=(env_fallback, ["INFRAHUB_API_TOKEN"])),
    state=dict(required=False, default="present", choices=["present", "absent"]),
    validate_certs=dict(type="bool", default=True),
    timeout=dict(required=False, type="int", default=10),
)

if HAS_INFRAHUBCLIENT:
    TYPE_MAPPING = {"str": str, "int": int, "float": float, "bool": bool}

    def get_node_identifier(node: InfrahubNodeSync) -> str:
        """
        Return an identifier for the node
        Prefer the HFID if available; otherwise, use the ID

        Parameters:
            node (InfrahubNodeSync): A node instance

        Returns:
            str: identifier for the node as a string

        """
        if node.hfid:
            return str(node.get_human_friendly_id())
        if node.id:
            return str(node.id)
        return "unknown"

    class InfrahubclientWrapper:
        def __init__(  # noqa: PLR0917
            self,
            api_endpoint: str,
            token: str,
            branch: str | None = None,
            timeout: int | None = 10,
            validate_certs: bool | None = True,
            display: Display | None = None,
        ):
            """
            Initializes InfrahubclientWrapper.

            Parameters:
                api_endpoint (str): API endpoint for the Infrahub service.
                token (str): Infrahub API token.
                branch (str, optional): Branch in which the request is made.
                timeout (int, optional): Timeout for Infrahub requests in seconds.
                validate_certs (bool, optional): Whether or not to validate SSL of the Infrahub instance. Defaults to True
                display (Display, optional): Ansible Display to use during during execution. Defaults to None.
            """
            if not isinstance(validate_certs, bool):
                raise ValueError(f"validate_certs must be a bool, got {type(validate_certs).__name__}")

            if branch:
                self.client = InfrahubClientSync(
                    address=api_endpoint,
                    config=Config(
                        api_token=token, timeout=timeout, default_branch=branch, tls_insecure=not validate_certs
                    ),
                )
            else:
                self.client = InfrahubClientSync(
                    address=api_endpoint,
                    config=Config(api_token=token, timeout=timeout, tls_insecure=not validate_certs),
                )
            self.display = display
            for method_name in dir(self):
                if callable(getattr(self, method_name)) and not method_name.startswith("_"):
                    original_method = getattr(self, method_name)
                    decorated_method = handle_infrahub_exceptions_decorator(self.display)(original_method)
                    setattr(self, method_name, decorated_method)

        def fetch_single_artifact(
            self,
            filters: dict[str, str],
            branch: str | None = None,
        ) -> dict[str, Any]:
            """
            Retrieve all artifact content

            Parameters:
                filters (dict[str, str], optional): dict of filters to apply on the query
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

        def generate_artifact(
            self,
            filters: dict[str, str],
            target_id: str,
            branch: str = "main",
        ) -> dict[str, Any]:
            """
            Trigger regeneration of an artifact for the given target node.

            Parameters:
                filters (dict[str, str]): Filters to locate the artifact
                    - For artifact_name: {"name__value": name}
                    - For artifact_id: {"ids": [artifact_id]}
                target_id (str): Target node UUID to regenerate the artifact for
                branch (str, optional): Name of the branch. Defaults to default_branch.

            Returns:
                dict: Results including regeneration status
            """
            result: dict[str, Any] = {
                "artifact_name": filters.get("name__value"),
                "artifact_id": None,
                "definition_id": None,
                "target_id": target_id,
                "changed": False,
                "failed": False,
                "msg": "",
            }

            # Step 1: Fetch the artifact node for the target_id
            lookup_filters = filters.copy()
            lookup_filters["object__ids"] = [target_id]
            node = self.fetch_single_node(
                kind="CoreArtifact",
                filters=lookup_filters,
                branch=branch,
            )

            if not node:
                result["failed"] = True
                result["msg"] = f"No artifact found for target '{target_id}' with filters: {filters}"
                return result

            result["artifact_id"] = node.id
            result["artifact_name"] = node.name.value
            result["definition_id"] = node.definition.id

            # Step 2: Trigger regeneration using the artifact ID
            url = f"{self.client.address}/api/artifact/generate/{result['definition_id']}?branch={branch}"
            payload = {"nodes": [target_id]}
            try:
                resp = self.client._post(url=url, payload=payload)
                resp.raise_for_status()
            except Exception as exc:
                result["failed"] = True
                result["msg"] = (
                    f"Failed to trigger artifact regeneration for definition '{result['definition_id']}': {exc}"
                )
                return result

            # Step 3: Return success
            result["changed"] = True
            result["msg"] = f"Successfully triggered regeneration for artifact '{result['artifact_name']}'"
            return result

        def fetch_artifacts(
            self,
            filters: dict[str, str] | None = None,
            branch: str | None = None,
        ) -> list[dict[str, Any]]:
            """
            Retrieve all artifact content

            Parameters:
                filters (dict[str, str], optional): dict of filters to apply on the query
                branch (str, optional): Name of the branch to query from. Defaults to default_branch.

            Returns:
                list[dict]: list of Artifact Content
            """
            order = Order(disable=True)
            results: list[dict[str, Any]] = []
            nodes = self.fetch_nodes(
                kind="CoreArtifact",
                filters=filters,
                branch=branch,
                order=order,
            )
            for node in nodes:
                resp = self.client._get(url=f"{self.client.address}/api/storage/object/{node.storage_id.value}")
                result: dict[str, Any] = {
                    "json": None,
                    "text": None,
                }
                if node.content_type.value == "application/json":
                    result["json"] = resp.json()
                else:
                    result["text"] = resp.text

                results.append(result)
            return results

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
            raise_when_missing: bool | None = False,
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
                raise_when_missing (bool, optional): Whether we want to raise an Exception in case of missing object. Defaults to False.

            Returns:
                InfrahubNodeSync: Single Infrahub Node
            """
            if not filters and not hfid and not id:
                raise Exception("At least one filter must be provided.")

            if filters:
                node = self.client.get(
                    kind=kind,
                    id=id,
                    hfid=hfid,
                    include=include,
                    populate_store=True,
                    exclude=exclude,
                    branch=branch,
                    prefetch_relationships=prefetch_relationships,
                    raise_when_missing=raise_when_missing,
                    **filters,
                )
            else:
                node = self.client.get(
                    kind=kind,
                    id=id,
                    hfid=hfid,
                    include=include,
                    populate_store=True,
                    exclude=exclude,
                    branch=branch,
                    prefetch_relationships=prefetch_relationships,
                    raise_when_missing=raise_when_missing,
                )
            return node

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
            nodes: list[InfrahubNodeSync] = []

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

        def fetch_single_schema(
            self,
            kind: str,
            branch: str | None = None,
            raise_when_missing: bool | None = True,
        ) -> NodeSchemaAPI | GenericSchemaAPI | ProfileSchemaAPI:
            """
            Retrieves schema attributes for the given kind.

            Parameters:
                kind (str): The kind for which the schema attributes are needed.
                branch (str, optional): Name of the branch to query from. Defaults to default_branch.
                raise_when_missing (bool, optional): Whether to raise an exception if the schema is not found. Defaults to True.

            Returns:
                NodeSchemaAPI | GenericSchemaAPI | ProfileSchemaAPI: The schema attributes for the given kind.
            """
            if raise_when_missing:
                return self.client.schema.get(kind=kind, branch=branch)
            try:
                return self.client.schema.get(kind=kind, branch=branch)
            except SchemaNotFoundError:
                return None

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
            branch = branch or self.client.config.default_branch
            return self.client.schema.all(branch=branch)

        def fetch_branchs(self) -> dict[str, BranchData]:
            """
            Retrieves all available branches.

            Returns:
                dict[str, BranchData]: A dictionary containing all branches.
            """
            return self.client.branch.all()

        def fetch_branch(self, name: str) -> BranchData:
            """
            Retrieves details of a specific branch.

            Parameters:
                name (str): The name of the branch to be fetched.

            Returns:
                BranchData: Details of the specified branch.
            """
            return self.client.branch.get(branch_name=name)

        def _render_query(self, query: dict, variables: dict | None = None) -> str:
            """
            Render a GraphQL Query from a dict to a String

            Parameters:
                query (dict): GraphQL Query to render, can be a query or a mutation
                variables (dict, optional): Variables to pass along with the GraphQL query. Defaults to None.

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

        def execute_graphql(
            self, query: str, variables: dict[str, Any] | None = None, branch: str | None = None
        ) -> dict:
            """
            Executes a GraphQL query against the Infrahub Endpoint.

            Parameters:
                query (str): The GraphQL query string to execute.
                variables (dict, optional): Variables to pass along with the GraphQL query. Defaults to None.
                branch (str, optional): Name of the branch to query from. Defaults to default_branch.

            Returns:
                dict: The result of the executed GraphQL query.
            """
            # TODO: Do something with the variables ?
            response = self.client.execute_graphql(query=query, variables=variables, branch_name=branch)
            return response

        def create_node(self, kind: str, data: dict, branch: str | None = None, **kwargs: Any) -> InfrahubNodeSync:
            """
            Create a new node of given kind with provided attributes

            Parameters:
                kind (str): The Kind of the Object to create
                data (dict): The data for this object
                branch (str, optional): Name of the branch to use. Defaults to default_branch.

            Returns:
                BranchData | str: Details of the specified branch.
            """
            return self.client.create(kind=kind, data=data, branch=branch, kwargs=kwargs)

        def create_branch(
            self, name: str, description: str | None = "", sync_with_git: bool = False
        ) -> BranchData | str:
            """
            Create a new InfrahubBranch with provided attributes

            Parameters:
                name (str): The name of the branch to create
                description (str, optional): The description of the branch
                sync_with_git (bool, optional): If Infrahub have to extend the branch to Git

            Returns:
                BranchData | str: Details of the specified branch.
            """
            return self.client.branch.create(branch_name=name, description=description, sync_with_git=sync_with_git)

        def delete_branch(self, name: str) -> bool:
            """
            Delete a InfrahubBranch

            Parameters:
                name (str): The name of the branch to delete

            Returns:
                bool: result of the mutation ["BranchDelete"]["ok"].
            """
            return self.client.branch.delete(branch_name=name)

        @staticmethod
        def save_node(node: InfrahubNodeSync, allow_upsert: bool = True) -> None:
            """
            Save changes to a node
            """
            node.save(allow_upsert=allow_upsert)

        @staticmethod
        def delete_node(node: InfrahubNodeSync) -> None:
            """
            Save changes to a node
            """
            node.delete()

    class InfrahubBaseProcessor:
        def __init__(
            self,
            client: InfrahubclientWrapper,
            display: Display | None = None,
        ):
            self.client = client
            self.display = display

        def _handle_display(
            self, message: str, exception: Exception | None = None, level: str | None = "ERROR"
        ) -> None:
            error_msg = f"{message}"
            if exception:
                error_msg = f"{message}: {exception!s}"
            if self.display:
                self.display.debug(error_msg)
                if level == "ERROR":
                    self.display.error(error_msg)
                elif level == "WARNING":
                    self.display.warning(error_msg)
                elif level == "INFO":
                    self.display.v(error_msg)
                elif level == "DEBUG":
                    self.display.debug(error_msg)

        @staticmethod
        def deep_update(source: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
            """
            Update a nested dictionary or similar mapping.
            Modify ``source`` in place.
            """
            for key, value in overrides.items():
                if isinstance(value, dict) and value:
                    returned = InfrahubBaseProcessor.deep_update(source.get(key, {}), value)
                    source[key] = returned
                else:
                    source[key] = value
            return source

        @staticmethod
        def _parse_attrs(attrs: list[str]) -> dict[str, dict[str, Any]]:
            """
            Pre-process attrs: parse once and group by root attribute.

            Parameters:
                attrs: List of attribute names (e.g., ["name", "tags.name", "tags.display_label"])

            Returns:
                dict: Structure {root_attr: {"nested": [nested_attrs], "has_simple": bool}}
            """
            parsed: dict[str, dict[str, Any]] = {}
            for attr in attrs:
                dot_idx = attr.find(".")
                if dot_idx > 0:
                    root, nested = attr[:dot_idx], attr[dot_idx + 1 :]
                    if root not in parsed:
                        parsed[root] = {"nested": [], "has_simple": False}
                    parsed[root]["nested"].append(nested)
                else:
                    if attr not in parsed:
                        parsed[attr] = {"nested": [], "has_simple": False}
                    parsed[attr]["has_simple"] = True
            return parsed

        def _resolve_schema_attribute(self, node: InfrahubNodeSync, root_attr: str, node_attr: Any) -> str | None:
            """Resolve a schema attribute value, handling inherited attributes."""
            if node_attr.value:
                return str(node_attr.value)
            # FIXME: If the attribute is inherited, it's not populated properly in store
            tmp_node = node._client.get(id=node.id, kind=node._schema.kind)
            tmp_attr = getattr(tmp_node, root_attr, None)
            return str(tmp_attr.value) if tmp_attr.value else tmp_attr.value

        def _resolve_many_relationship(
            self, node_attr: RelationshipManagerSync, nested_attrs: list[str], has_nested: bool, schemas: dict[str, Any]
        ) -> list[Any]:
            """Resolve a many-cardinality relationship (RelationshipManagerSync)."""
            store = self.client.client.store
            peers: list[Any] = []

            if not node_attr.peers:
                node_attr.fetch()

            for peer in node_attr.peers:
                related_node = store.get(key=peer.id, raise_when_missing=False)
                if not related_node:
                    peer.fetch()
                    related_node = peer.peer

                if not related_node or not hasattr(related_node._schema, "attribute_names"):
                    continue

                if has_nested:
                    peer_data: dict[str, Any] = {"id": related_node.id}
                    nested_result = self.resolve_node_mapping(
                        node=related_node, attrs=nested_attrs, schemas=schemas, include_id=False
                    )
                    if nested_result:
                        peer_data.update(nested_result)
                    peers.append(peer_data)
                else:
                    peers.append(related_node.id)

            return peers

        def _resolve_one_relationship(
            self, node_attr: RelatedNodeSync, nested_attrs: list[str], has_nested: bool, schemas: dict[str, Any]
        ) -> dict[str, Any] | str | None:
            """Resolve a one-cardinality relationship (RelatedNodeSync)."""
            if not (node_attr.id and node_attr.schema.peer):
                return None

            store = self.client.client.store
            related_node = store.get(key=node_attr.id, raise_when_missing=False)
            if not related_node:
                node_attr.fetch()
                related_node = node_attr.peer

            if not related_node:
                return None

            if has_nested:
                return self.resolve_node_mapping(
                    node=related_node, attrs=nested_attrs, schemas=schemas, include_id=True
                )
            return related_node.id

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
            attribute_dict: dict[str, Any] = {}
            node_schema = node._schema
            parsed_attrs = self._parse_attrs(attrs)

            for root_attr, attr_info in parsed_attrs.items():
                nested_attrs, has_simple, has_nested = (
                    attr_info["nested"],
                    attr_info["has_simple"],
                    bool(attr_info["nested"]),
                )
                node_attr = getattr(node, root_attr, None)
                attribute_dict[root_attr] = {} if has_nested else None

                # Handle special node properties (display_label, hfid)
                if root_attr in ("display_label", "hfid") and has_simple and not has_nested:
                    attribute_dict[root_attr] = getattr(node, root_attr, None)
                    continue

                if node_attr is None:
                    continue

                # Handle schema attributes
                if root_attr in node_schema.attribute_names and has_simple and not has_nested:
                    attribute_dict[root_attr] = self._resolve_schema_attribute(node, root_attr, node_attr)

                # Handle relationships
                elif root_attr in node_schema.relationship_names:
                    if isinstance(node_attr, RelationshipManagerSync):
                        peers = self._resolve_many_relationship(node_attr, nested_attrs, has_nested, schemas)
                        if peers:
                            attribute_dict[root_attr] = peers
                    elif isinstance(node_attr, RelatedNodeSync):
                        result = self._resolve_one_relationship(node_attr, nested_attrs, has_nested, schemas)
                        if result is not None:
                            attribute_dict[root_attr] = result

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
            # From https://docs.infrahub.app/python-sdk/guides/query_data#attributes-and-relationships
            #  By default, the result of a query will include attributes, relationships of cardinality one
            #  and relationships of kind Attribute or Parent
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
                try:
                    nodes_from_kind = self.client.fetch_nodes(
                        kind=node_kind,
                        include=include,
                        exclude=exclude,
                        filters=filters,
                        prefetch_relationships=prefetch_relationships,
                        order=order,
                    )
                except Exception as exc:
                    self._handle_display(
                        exception=exc,
                        message=f"Failed to fetch_nodes for kind '{node_kind}'",
                        level="WARNING",
                    )
                    continue

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
                self._handle_display(
                    message=f"Prefetching schema for related nodes of kind '{node_kind}'",
                    level="DEBUG",
                )
                for related_kind in related_kinds:
                    schema_dict[related_kind] = self.client.fetch_single_schema(kind=related_kind)
                    self._handle_display(
                        message=f"Prefetching related nodes for kind '{related_kind}'",
                        level="DEBUG",
                    )
                    try:
                        self.client.fetch_nodes(kind=related_kind, prefetch_relationships=False, order=order)
                    except Exception as exc:
                        self._handle_display(
                            exception=exc,
                            message=f"Failed to fetch_nodes for kind '{related_kind}'",
                            level="WARNING",
                        )
                        continue
                for host_node in all_nodes:
                    result = self.resolve_node_mapping(
                        node=host_node,
                        attrs=node_attributes_dict[host_node._schema.kind],
                        schemas=schema_dict,
                        include_id=include_id,
                    )
                    self._handle_display(
                        message=f"Resolved attributes for node '{get_node_identifier(host_node)}'",
                        level="DEBUG",
                    )
                    if result:
                        host_node_attributes[str(host_node)] = result

            return host_node_attributes

        @staticmethod
        def resolve_dotted_path(attributes: dict, path: str) -> str | None:
            """Resolve a dotted attribute path (e.g. 'primary_address.address') through a nested dict."""
            current = attributes
            for part in path.split("."):
                if not isinstance(current, dict) or part not in current:
                    return None
                current = current[part]
            return current if isinstance(current, str) else None

        def resolve_hostnames(self, host_node_attributes: dict[str, Any], hostnames: list[str]) -> dict[str, Any]:
            """Re-key host_node_attributes based on the hostnames priority list.

            Parameters:
                host_node_attributes (dict[str, Any]): A dictionary with processed host node attributes.
                hostnames (list[str]): A list of attribute paths to try in order.

            Returns:
                dict[str, Any]: A new dictionary re-keyed by the first matching hostname.
            """
            if not hostnames:
                return host_node_attributes

            result: dict[str, Any] = {}
            for original_key, attributes in host_node_attributes.items():
                new_key = None
                for path in hostnames:
                    if path == "display_label":
                        resolved = self.resolve_dotted_path(attributes, path)
                        new_key = resolved or original_key
                        break
                    resolved = self.resolve_dotted_path(attributes, path)
                    if resolved:
                        new_key = resolved
                        break

                if not new_key:
                    new_key = original_key

                if new_key in result:
                    self._handle_display(
                        message=f"Duplicate hostname '{new_key}' found, last entry wins.",
                        level="WARNING",
                    )
                result[new_key] = attributes

            return result

        def create_node(self, kind: str, data: dict) -> InfrahubNodeSync:
            """
            Create a node after validating required fields against schema

            Parameters:
                kind (str): The Kind of the Object to create
                data (dict): The data for this object

            Returns:
                InfrahubNodeSync: the node created in Infrahub
            """
            schema = self.client.fetch_single_schema(kind=kind, raise_when_missing=False)
            if not schema:
                raise Exception(f"Non-existing kind '{kind}'")

            # TODO: Should be replace after https://github.com/opsmill/infrahub-sdk-python/issues/268
            validation_errors = []
            validation_errors.extend(
                f"Required attribute '{attr.name}' missing for '{kind}"
                for attr in schema.attributes
                if not attr.optional and not attr.read_only and attr.default_value is None and attr.name not in data
            )
            validation_errors.extend(
                f"Required relationship '{rel.name}' missing for '{kind}'"
                for rel in schema.relationships
                if not rel.optional and rel.name not in data
            )
            validation_errors.extend(
                f"Field '{field}' is not defined for kind '{kind}'"
                for field in data
                if field not in schema.attribute_names + schema.relationship_names
            )

            if validation_errors:
                raise Exception(f"Validation failed: {', '.join(validation_errors)}")

            try:
                node = self.client.create_node(kind=kind, data=data)
            except Exception as exc:
                raise Exception(f"Failed to create node with {data} for kind '{kind}' due to {exc}")

            return node

        def save_node(self, node: InfrahubNodeSync) -> None:
            """
            Save a node

            Parameters:
                node (InfrahubNodeSync): the node to save in Infrahub
            """
            try:
                self.client.save_node(node=node)
            except Exception as exc:
                raise Exception(f"Failed to save node {node} {exc}")

            # TODO: Improve this check -> If there is no ID, it mean that the save failed. Reason ?
            if not node.id:
                raise Exception(f"Failed to save node {node}")

        def delete_node(self, node: InfrahubNodeSync) -> bool:
            """
            Delete a node from Infrahub

            """
            try:
                self.client.delete_node(node=node)

            except Exception as exc:
                self._handle_display(
                    exception=exc,
                    message=f"Failed to delete node with {node}",
                    level="ERROR",
                )
                raise

            return node

        def create_branch(
            self, name: str, description: str | None = "", sync_with_git: bool = False
        ) -> BranchData | str:
            """
            Create an InfrahubBranch

            Parameters:
                name (str): The name of the branch to create
                description (str, optional): The description of the branch
                sync_with_git (bool, optional): If Infrahub have to extend the branch to Git

            Returns:
                BranchData | str: Details of the specified branch.
            """
            try:
                branch_data = self.client.create_branch(name=name, description=description, sync_with_git=sync_with_git)
            except Exception as exc:
                raise Exception(f"Failed to create InfrahubBranch with '{name}' due to {exc}")
            if not branch_data:
                raise Exception(f"Failed to create InfrahubBranch with '{name}'")

            return branch_data

        def delete_branch(self, name: str) -> bool:
            """
            Delete an InfrahubBranch

            Parameters:
                name (str): The name of the branch to delete

            Returns:
                BranchData  |str: Details of the specified branch.
            """
            try:
                success = self.client.delete_branch(name=name)
            except Exception as exc:
                raise Exception(f"Failed to delete InfrahubBranch with '{name}' due to {exc}")
            if not success:
                raise Exception(f"Failed to delete InfrahubBranch with '{name}'")
            return success

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

            if isinstance(query, dict):
                query_str = self.client._render_query(query=query, variables=variables)
            elif isinstance(query, str):
                query_str = query
            else:
                raise Exception("query is neither a string nor a dict")

            try:
                results = {}
                response = self.client.execute_graphql(query=query_str, variables=variables)
                if not response:
                    raise Exception

            except Exception:
                raise Exception(f"Failed to execute the grapqhl query '{query}'")

            if any(key.endswith(("Create", "Update", "Delete")) for key in response):
                # Handle mutation response
                mutation_key = next(key for key in response if key.endswith(("Create", "Update", "Delete")))
                mutation_data = response[mutation_key]
                if mutation_data.get("ok"):
                    if "object" in mutation_data:  # Create/Update will have object
                        results = mutation_data.get("object", {})
                else:
                    raise Exception(f"Mutation failed: {mutation_data.get('error', '')}'")

            # Handle query response
            else:
                results = response

            return results

    class InfrahubModule:
        """
        Initialize connection to Infrahub
        sets AnsibleModule passed in to self.module to be used throughout the class

        Parameters:
            module (AnsibleModule): Ansible Module object
            client (InfrahubclientWrapper): Wrapper to interract with Infrahub API

        """

        def __init__(self, module: AnsibleModule, client: InfrahubclientWrapper | None = None) -> None:
            self.module = module
            self.state = self.module.params["state"]
            self.check_mode = self.module.check_mode

            api_endpoint = self.module.params.get("api_endpoint")
            token = self.module.params.get("token")
            if api_endpoint is None:
                self.module.fail_json(msg="Missing Infrahub API Endpoint")
            if token is None:
                self.module.fail_json(msg="Missing Infrahub TOKEN")

            api_endpoint = api_endpoint.strip("/")

            validate_certs = self.module.params.get("validate_certs")

            if not isinstance(validate_certs, bool):
                self.module.fail_json(msg="validate_certs must be a boolean")

            timeout = self.module.params.get("timeout")
            branch = self.module.params.get("branch")

            try:
                if client is None:
                    self.client = InfrahubclientWrapper(
                        api_endpoint=api_endpoint,
                        token=token,
                        branch=branch,
                        timeout=timeout,
                        validate_certs=validate_certs,
                    )
                else:
                    self.client = client
            except Exception as exc:
                self._handle_errors(msg=str(exc))

            # TODO: cleanup and normalized data ?
            self.data = module.params

        def _handle_errors(self, msg: Any):
            """
            Returns message and changed = False

            Parameters:
                msg (Any): Message indicating why there is no change
            """
            self.module.fail_json(msg=msg, changed=False)

        def _build_diff(self, before: dict | None, after: dict | None) -> dict:
            """
            Builds diff of before and after changes

            Parameters:
                before (dict): Data before the change
                after (dict): Data after the change

            Returns:
                dict: Ansible Diff Before and After
            """
            return {"before": before, "after": after}

        # TODO: Should be replace after https://github.com/opsmill/infrahub-sdk-python/issues/267
        def rebuild_hfid_from_data(
            self, schema: NodeSchemaAPI | GenericSchemaAPI | ProfileSchemaAPI, data: dict
        ) -> list[str] | None:
            """
            Rebuild the HFID filters from the provided data based on a schema human_friendly_id.

            For each composite key in schema.human_friendly_id, split it into individual keys.
            Then, for each key, get its value from the flat data. If all parts are found,
            join them together to form a filter string.

            Parameters:
                schema: An object that has a 'human_friendly_id' attribute (a list of composite key strings).
                data (dict): The flat data provided by the user.

            Returns:
                list[str]: A list of filter strings. If some fields are missing, returning None
            """
            hfid_values = []
            # Iterate over each composite key defined in the schema.
            for composite in schema.human_friendly_id:
                # Split the composite key into individual field names.
                element = composite.split("__")[0]
                value = data.get(element)
                if value is None:
                    return None
                hfid_values.append(str(value))

            return hfid_values

        def _get_branch(self, name: str) -> BranchData | None:
            """
            Retrieve a single branch using the branch name

            Parameters:
                name (str): The name of the InfrahubBranch

            Returns:
                BranchData | None: The BranchData or None if not found.
            """
            try:
                node = self.client.fetch_branch(name=name)
            # TODO: Until https://github.com/opsmill/infrahub-sdk-python/issues/269
            except Exception as exc:
                if exc.__class__ == BranchNotFoundError:
                    return None

                self._handle_errors(
                    f"An error occurred while retrieving InfrahubBranch {name} due to {exc.__class__} {exc}"
                )
            return node

        def _get_object(
            self, schema: NodeSchemaAPI | GenericSchemaAPI | ProfileSchemaAPI, kind: str, data: dict
        ) -> InfrahubNodeSync | None:
            """
            Build filters based on the data, and retrieve a single object with these filters

            Parameters:
                kind (str): The Kind of the Object to create
                data (dict): The data for this object

            Returns:
                InfrahubNodeSync: The node or None if not found.
            """
            node_id = data.get("id")
            node_hfid = data.get("hfid")

            if not node_id and not node_hfid and schema.human_friendly_id:
                node_hfid = self.rebuild_hfid_from_data(schema, data)
            if not node_id and not node_hfid:
                # TODO: Should we build filters from data, example: data["name"] => name__value
                pass
            try:
                node = self.client.fetch_single_node(kind=kind, id=node_id, hfid=node_hfid, raise_when_missing=False)
            except Exception as exc:
                self._handle_errors(f"An error occurred while retrieving {kind} {data} due to {exc}")

            return node

        def _create_branch(self, data: dict) -> tuple[InfrahubNodeSync, dict]:
            """
            Create an InfrahubBranch after validating required fields.

            Parameters:
                data (dict): The data for this object

            Returns:
                tuple(object, diff): tuple of the InfrahubNodeSync created in Infrahub and the Ansible diff.
            """
            processor = InfrahubNodesProcessor(client=self.client)
            branch_name = data.get("name")
            branch_description = data.get("description") or ""
            sync_with_git = data.get("sync_with_git")
            try:
                branch = processor.create_branch(
                    name=branch_name, description=branch_description, sync_with_git=sync_with_git
                )
            except Exception as exc:
                self._handle_errors(msg=str(exc))

            diff = self._build_diff(before={"state": "absent"}, after={"state": "present"})
            return branch, diff

        def _delete_branch(self, name: str) -> dict:
            """
            Delete an InfrahubBranch.

            Parameters:
                name (str): The name of the branch to delete

            Returns:
                dict: Ansible diff.
            """
            try:
                processor = InfrahubNodesProcessor(client=self.client)
                processor.delete_branch(name=name)
            except Exception as exc:
                self._handle_errors(msg=str(exc))

            diff = self._build_diff(before={"state": "present"}, after={"state": "absent"})
            return diff

        def _create_object(self, kind: str, data: dict) -> tuple[InfrahubNodeSync, dict]:
            """
            Create an Infrahub Object.

            Parameters:
                kind (str): The Kind of the Object to create
                data (dict): The data for this object

            Returns:
                tuple(object, diff): tuple of the InfrahubNodeSync created in Infrahub and the Ansible diff.
            """
            processor = InfrahubNodesProcessor(client=self.client)
            try:
                node = processor.create_node(kind=kind, data=data)
                if not self.check_mode:
                    processor.save_node(node=node)
            except Exception as exc:
                self._handle_errors(msg=str(exc))

            diff = self._build_diff(before={"state": "absent"}, after={"state": "present"})
            return node, diff

        def _normalize_rel_id_to_hfid(self, rel_name: str, rel_value: Any) -> Any:  # noqa: PLR0911
            """
            Normalize relationship IDs to HFIDs by looking up nodes in the store.
            This ensures consistent comparison when user provides HFID but stored data has UUID.

            Parameters:
                rel_name (str): The name of the relationship
                rel_value (Any): The relationship value from serialized data (contains UUIDs)

            Returns:
                Any: The normalized relationship value with HFIDs instead of UUIDs
            """
            if rel_value is None:
                return None

            rel_schema = next(
                (rel for rel in self.infrahub_node._schema.relationships if rel.name == rel_name),
                None,
            )
            if not rel_schema:
                return rel_value

            def get_or_fetch_node(node_id: str) -> InfrahubNodeSync | None:
                """Get node from store or fetch it (without prefetch to avoid recursion)."""
                related_node = self.client.client.store.get(key=node_id, raise_when_missing=False)
                if related_node:
                    return related_node
                # Node not in store, fetch it directly
                try:
                    related_node = self.client.client.get(
                        kind=rel_schema.peer,
                        id=node_id,
                        populate_store=True,
                        prefetch_relationships=False,
                    )
                    return related_node
                except Exception:
                    return None

            def normalize_to_hfid_format(related_node: InfrahubNodeSync) -> dict[str, Any]:
                """Convert node's HFID to the format used by _generate_input_data().

                Single-element HFID: {"id": "value"} (string)
                Multi-element HFID: {"hfid": ["value1", "value2"]} (list with hfid key)
                """
                hfid = related_node.hfid  # This is a list
                if hfid and len(hfid) == 1:
                    return {"id": hfid[0]}
                return {"hfid": hfid}

            # Handle cardinality ONE relationships
            if rel_schema.cardinality == RelationshipCardinality.ONE:
                if isinstance(rel_value, dict) and "id" in rel_value:
                    node_id = rel_value["id"]
                    # Only normalize if the ID is a UUID, not if it's already an HFID
                    if is_valid_uuid(node_id):
                        related_node = get_or_fetch_node(node_id)
                        if related_node and related_node.hfid:
                            return normalize_to_hfid_format(related_node=related_node)
                return rel_value

            # Handle cardinality MANY relationships
            if rel_schema.cardinality == RelationshipCardinality.MANY:
                if isinstance(rel_value, list):
                    normalized = []
                    for item in rel_value:
                        if isinstance(item, dict) and "id" in item:
                            node_id = item["id"]
                            # Only normalize if the ID is a UUID, not if it's already an HFID
                            if is_valid_uuid(node_id):
                                related_node = get_or_fetch_node(node_id)
                                if related_node and related_node.hfid:
                                    normalized.append(normalize_to_hfid_format(related_node=related_node))
                                else:
                                    normalized.append(item)
                            else:
                                normalized.append(item)
                        else:
                            normalized.append(item)
                    return normalized
                return rel_value

            return rel_value

        def _normalize_rel_format(self, rel_value: Any) -> Any:
            """
            Normalize relationship value format to a canonical form.
            Converts {"hfid": ["single"]} to {"id": "single"} for consistency.

            Parameters:
                rel_value (Any): The relationship value from serialized data

            Returns:
                Any: The normalized relationship value in canonical format
            """
            if rel_value is None:
                return None

            def normalize_single(item: Any) -> Any:
                """Normalize a single relationship item."""
                # Convert {"hfid": ["single"]} to {"id": "single"}
                if (
                    isinstance(item, dict)
                    and "hfid" in item
                    and isinstance(item["hfid"], list)
                    and len(item["hfid"]) == 1
                ):
                    return {"id": item["hfid"][0]}
                return item

            if isinstance(rel_value, dict):
                return normalize_single(rel_value)
            if isinstance(rel_value, list):
                return [normalize_single(item) for item in rel_value]

            return rel_value

        def _update_object(self, data: dict) -> tuple[InfrahubNodeSync, dict]:
            """
            Update an Infrahub Object.

            Parameters:
                data (dict): The data for this object

            Returns:
                tuple(object, diff): tuple of the InfrahubNodeSync created in Infrahub and the Ansible diff.
            """
            # Capture the "before" state by serializing the original node's data
            # We avoid using deepcopy on the node because InfrahubNodeSync contains
            # a reference to InfrahubClientSync which has an SSLContext that cannot be pickled
            serialized_before = deepcopy(self.infrahub_node._generate_input_data().get("data", {}).get("data", {}))

            # Normalize relationship UUIDs to HFIDs in the "before" state
            # This ensures consistent comparison when user provides HFID but stored data has UUID
            for key in list(serialized_before.keys()):
                if key in self.infrahub_node._schema.relationship_names:
                    serialized_before[key] = self._normalize_rel_id_to_hfid(key, serialized_before.get(key))
                    # Also normalize the format (e.g., {"hfid": ["single"]} -> {"id": "single"})
                    serialized_before[key] = self._normalize_rel_format(serialized_before[key])

            # TODO: SDK should provide a way to do that
            # https://github.com/opsmill/infrahub-sdk-python/issues/272
            for attr_name in data:
                if attr_name in self.infrahub_node._schema.attribute_names:
                    setattr(
                        self.infrahub_node,
                        attr_name,
                        data.get(attr_name),
                    )
                elif attr_name in self.infrahub_node._schema.relationship_names:
                    rel_schema = next(rel for rel in self.infrahub_node._schema.relationships if rel.name == attr_name)
                    rel_data = data.get(attr_name)
                    if rel_schema.cardinality == RelationshipCardinality.ONE:
                        setattr(self.infrahub_node, f"_{attr_name}", None)
                        setattr(
                            self.infrahub_node,
                            attr_name,
                            rel_data,
                        )
                    elif rel_schema.cardinality == RelationshipCardinality.MANY:
                        setattr(
                            self.infrahub_node,
                            attr_name,
                            RelationshipManagerSync(
                                name=attr_name,
                                client=self.infrahub_node._client,
                                node=self.infrahub_node,
                                branch=self.infrahub_node._branch,
                                schema=rel_schema,
                                data=rel_data,
                            ),
                        )

            # TODO: SDK should provide a way to do that too ...
            # https://github.com/opsmill/infrahub-sdk-python/issues/271
            serialized_after = self.infrahub_node._generate_input_data().get("data", {}).get("data", {})

            # Normalize relationship formats in the "after" state to match "before" canonical format
            # This handles cases where _generate_input_data() produces {"hfid": ["single"]} but we normalized to {"id": "single"}
            for key in list(serialized_after.keys()):
                if key in self.infrahub_node._schema.relationship_names:
                    serialized_after[key] = self._normalize_rel_format(serialized_after.get(key))

            if dict_hash(serialized_before) == dict_hash(serialized_after):
                return self.infrahub_node, None

            data_before, data_after = {}, {}
            for key in data:
                key_before = serialized_before.get(key)
                key_after = serialized_after.get(key)
                if key_before != key_after:
                    data_before[key] = key_before
                    data_after[key] = key_after

            if not self.check_mode:
                self.infrahub_node.update()

            diff = self._build_diff(before=data_before, after=data_after)
            return self.infrahub_node, diff

        def _delete_object(self) -> dict:
            """
            Delete an Infrahub Object.

            Returns:
                dict: Ansible diff.
            """
            if not self.check_mode:
                try:
                    processor = InfrahubNodesProcessor(client=self.client)
                    processor.delete_node(self.infrahub_node)
                except Exception as exc:
                    self._handle_errors(msg=str(exc))

            diff = self._build_diff(before={"state": "present"}, after={"state": "absent"})
            return diff

        def _ensure_branch_exists(self, data: dict) -> None:
            """
            Used when `state` is present to make sure an InfrahubBranch exists

            Parameters:
                data (dict):  User defined data passed into the module
            """
            identifier = data.get("name")
            if not self.branch:
                self.result["msg"] = data
                self.branch, diff = self._create_branch(data=data)
                self.result["msg"] = f"InfrahubBranch {identifier} created"
                self.result["changed"] = True
                self.result["diff"] = diff
            else:
                # It is currently no possible to edit a Branch
                self.result["msg"] = f"InfrahubBranch {identifier} already exists."
                self.result["diff"] = None

        def _ensure_branch_absent(self, data: dict) -> None:
            """
            Used when `state` is absent to make sure an InfrahubBranch does not exist

            Parameters:
                kind (str): The Kind of the Object to create
                data (dict):  User defined data passed into the module
            """
            if not self.branch:
                self.result["msg"] = f"InfrahubBranch {data.get('name')} already absent"
            else:
                branch_name = data.get("name")
                diff = self._delete_branch(name=branch_name)
                self.result["msg"] = f"InfrahubBranch {branch_name} deleted"
                self.result["changed"] = True
                self.result["diff"] = diff

        def _ensure_object_exists(self, kind: str, data: dict) -> None:
            """
            Used when `state` is present to make sure an object exists.
            - if the object exists it will be updated
            - if the object does not exists it will be created

            Parameters:
                kind (str): The Kind of the Object to create
                data (dict):  User defined data passed into the module
            """
            object_data = data.get("data") or {}
            if not self.infrahub_node:
                self.result["msg"] = data
                self.infrahub_node, diff = self._create_object(kind=kind, data=object_data)
                identifier = get_node_identifier(node=self.infrahub_node)
                self.result["msg"] = f"{kind} {identifier} created"
                self.result["changed"] = True
                self.result["diff"] = diff
            else:
                self.infrahub_node, diff = self._update_object(data=object_data)
                identifier = get_node_identifier(node=self.infrahub_node)
                if diff:
                    self.result["msg"] = f"{kind} {identifier} updated"
                    self.result["changed"] = True
                    self.result["diff"] = diff
                else:
                    self.result["msg"] = f"{kind} {identifier} already exists"

        def _ensure_object_absent(self, kind: str, data: dict) -> None:
            """
            Used when `state` is absent to make sure an object does not exist
            - if the object exists it will be deleted
            - if the object does not exists we confirm it

            Parameters:
                kind (str): The Kind of the Object to create
                data (dict):  User defined data passed into the module
            """
            if not self.infrahub_node:
                self.result["msg"] = f"{kind} {data.get('data', {})} already absent"
            else:
                identifier = get_node_identifier(self.infrahub_node)
                diff = self._delete_object()
                self.result["msg"] = f"{kind} {identifier} deleted"
                self.result["changed"] = True
                self.result["diff"] = diff

        def run(self):
            """
            Must be implemented in subclasses
            """
            raise NotImplementedError


if not HAS_INFRAHUBCLIENT:

    class InfrahubclientWrapper:
        pass

    class InfrahubNodesProcessor:
        pass

    class InfrahubQueryProcessor:
        pass

    class InfrahubModule:
        pass
