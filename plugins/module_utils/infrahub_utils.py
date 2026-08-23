from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

import base64
import hashlib
import traceback
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ansible.module_utils.basic import env_fallback
from ansible_collections.opsmill.infrahub.plugins.module_utils.exception import handle_infrahub_exceptions_decorator
from ansible_collections.opsmill.infrahub.plugins.module_utils.metrics import RequestCounter, request_count
from ansible_collections.opsmill.infrahub.plugins.module_utils.peers import PeerWarmer, RefillLedger
from ansible_collections.opsmill.infrahub.plugins.module_utils.projection import NodeProjection

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

TEXT_MIME_TYPES = frozenset(
    {
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/json",
        "application/yaml",
        "application/x-yaml",
        "application/hcl",
        "application/graphql",
        "application/xml",
    }
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

            # Handed to the SDK as its recorder so the count is taken below pagination,
            # where the round-trips actually happen. Held here so callers can read it
            # back without reaching into the client's config.
            self.request_counter = RequestCounter()

            if branch:
                self.client = InfrahubClientSync(
                    address=api_endpoint,
                    config=Config(
                        api_token=token,
                        timeout=timeout,
                        default_branch=branch,
                        tls_insecure=not validate_certs,
                        custom_recorder=self.request_counter,
                    ),
                )
            else:
                self.client = InfrahubClientSync(
                    address=api_endpoint,
                    config=Config(
                        api_token=token,
                        timeout=timeout,
                        tls_insecure=not validate_certs,
                        custom_recorder=self.request_counter,
                    ),
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
            parallel: bool = True,
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
                parallel (bool, optional): Whether to page the query in parallel. Parallel mode spends an
                    extra round-trip on a count first, so it is a loss when the result fits one page.
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
                    parallel=parallel,
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
                    parallel=parallel,
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
            Delete a node
            """
            node.delete()

        @staticmethod
        def get_file_object_local_checksum(file_path: str) -> str:
            """
            Compute the SHA-1 checksum of a local file for idempotency comparison with
            the server-stored checksum on a CoreFileObject node.

            Parameters:
                file_path (str): Absolute or relative path to the local file.

            Returns:
                str: Lowercase hex digest of the SHA-1 hash.
            """
            return hashlib.sha1(Path(file_path).read_bytes(), usedforsecurity=False).hexdigest()

        def fetch_file_content(self, node: InfrahubNodeSync) -> dict[str, str | None]:
            """
            Download the binary content of a CoreFileObject node and return it as
            base64-encoded bytes plus an optional UTF-8 decoded text representation.

            Parameters:
                node (InfrahubNodeSync): An Infrahub node that inherits from CoreFileObject.

            Returns:
                dict: {"binary": base64_str, "text": str_or_None}
            """
            content: bytes = node.download_file()
            is_text = node.file_type.value in TEXT_MIME_TYPES
            return {
                "binary": base64.b64encode(content).decode("ascii"),
                "text": content.decode("utf-8", errors="replace") if is_text else None,
            }

        def fetch_file_object(
            self,
            kind: str,
            node_id: str | None = None,
            hfid: list[str] | None = None,
            branch: str | None = None,
        ) -> tuple[InfrahubNodeSync, bytes]:
            """
            Fetch a CoreFileObject node and download its binary file content.

            Parameters:
                kind (str): The schema node kind inheriting from CoreFileObject.
                node_id (str, optional): UUID of the node to fetch.
                hfid (list[str], optional): HFID components identifying the node.
                branch (str, optional): Branch to query. Defaults to default_branch.

            Returns:
                tuple: (InfrahubNodeSync, bytes) — the node and its raw file content.
            """
            node = self.fetch_single_node(
                kind=kind,
                id=node_id,
                hfid=hfid,
                branch=branch,
                raise_when_missing=True,
            )
            content: bytes = node.download_file()
            return node, content

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
                elif level == "VVV":
                    self.display.vvv(error_msg)
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

        def _resolve_schema_attribute(
            self,
            node: InfrahubNodeSync,
            root_attr: str,
            node_attr: Any,
            refetch_cache: dict[str, Any],
            refill: RefillLedger | None = None,
        ) -> Any:
            """Resolve a schema attribute value, handling attributes the query never carried.

            The return type is deliberately wide: a populated value is stringified, but a
            falsy-but-present one (``False``, ``0``, ``""``) is handed back as it came, so
            this is not ``str | None``. mypy does not currently check this file, so the
            annotation is the only thing saying so.

            An attribute can come back empty for two different reasons: the server
            answered null, or nobody asked for it. The second happens whenever the
            node was built from a relationship payload projected off a *generic* peer
            schema, which exposes fewer attributes than the concrete kind does.

            When ``refill`` is given, this records the node instead of refetching it, so
            the caller can load every affected node in one batched pass. Without it the
            node is refetched here and cached for the rest of this
            ``resolve_node_mapping`` call, so several empty attributes on one node cost
            one request rather than one each.
            """
            if node_attr.value:
                return str(node_attr.value)

            if refill is not None:
                # Only a genuinely absent value is worth reloading. `False`, `0` and
                # `""` are falsy but present, and the truthiness test above cannot
                # tell them from "never queried" -- so without this, a peer with a
                # boolean attribute set to False would be refetched and re-resolved
                # on every single run. The return value keeps the historical
                # truthiness semantics; only the decision to reload is narrowed.
                if node_attr.value is None:
                    refill.record(node, root_attr)
                return node_attr.value

            if "node" not in refetch_cache:
                refetch_cache["node"] = node._client.get(id=node.id, kind=node._schema.kind)
            tmp_attr = getattr(refetch_cache["node"], root_attr, None)
            return str(tmp_attr.value) if tmp_attr.value else tmp_attr.value

        def _resolve_many_relationship(
            self,
            node_attr: RelationshipManagerSync,
            nested_attrs: list[str],
            has_nested: bool,
            schemas: dict[str, Any],
            refill: RefillLedger | None = None,
        ) -> list[Any]:
            """Resolve a many-cardinality relationship (RelationshipManagerSync)."""
            store = self.client.client.store
            peers: list[Any] = []

            # Fetch only when the relationship has not been loaded yet. Guarding on
            # `initialized` (not `peers`) avoids re-fetching a relationship that was
            # already fetched but is genuinely empty (peers == [] in both cases).
            if not node_attr.initialized:
                node_attr.fetch()

            if not has_nested:
                # The result is the peer ids, which the relationship already carries.
                # Resolving each peer through the store (and fetching it when the store
                # misses) would spend a round-trip per peer to learn an id we hold.
                return [peer.id for peer in node_attr.peers if peer.id]

            for peer in node_attr.peers:
                related_node = store.get(key=peer.id, raise_when_missing=False)
                if not related_node:
                    peer.fetch()
                    related_node = peer.peer

                if not related_node or not hasattr(related_node._schema, "attribute_names"):
                    continue

                # include_id=True already prepends {"id": related_node.id}, matching
                # _resolve_one_relationship — no need to build/merge the dict by hand.
                nested_result = self.resolve_node_mapping(
                    node=related_node,
                    attrs=nested_attrs,
                    schemas=schemas,
                    include_id=True,
                    refill=refill,
                )
                if nested_result:
                    peers.append(nested_result)

            return peers

        def _resolve_one_relationship(
            self,
            node_attr: RelatedNodeSync,
            nested_attrs: list[str],
            has_nested: bool,
            schemas: dict[str, Any],
            refill: RefillLedger | None = None,
        ) -> dict[str, Any] | str | None:
            """Resolve a one-cardinality relationship (RelatedNodeSync)."""
            if not (node_attr.id and node_attr.schema.peer):
                return None

            if not has_nested:
                # The result is the peer id, which the relationship already carries.
                # Resolving the peer (and fetching it when the store misses) would spend
                # a round-trip per host node to learn an id we hold.
                return node_attr.id

            store = self.client.client.store
            related_node = store.get(key=node_attr.id, raise_when_missing=False)
            if not related_node:
                node_attr.fetch()
                related_node = node_attr.peer

            if not related_node:
                return None

            return self.resolve_node_mapping(
                node=related_node,
                attrs=nested_attrs,
                schemas=schemas,
                include_id=True,
                refill=refill,
            )

        def resolve_node_mapping(
            self,
            node: InfrahubNodeSync,
            attrs: list[str],
            schemas: dict[str, Any],
            include_id: bool = True,
            refill: RefillLedger | None = None,
        ) -> dict[str, Any] | None:
            """
            Resolve the attributes and relationships of a given node based on a list of desired attributes.

            Parameters:
                node (InfrahubNodeSync): The node to which attributes/relationships are to be mapped.
                attrs (list[str]): A list of attribute names that should be fetched for the node.
                schemas dict[str, Any]: A dictionary of Node Kind name, Any
                include_id (bool): Whether to include the node ID in the result. Defaults to True.
                refill (RefillLedger, optional): When given, nodes with an attribute the query
                    never carried are recorded there instead of being refetched one at a time, so
                    the caller can load them in a single batched pass.

            Returns:
                dict[str, Any]: A dictionary mapping attribute/relationship names to their respective values.
                        For relationship with "many" cardinality, it will be a list (of related nodes)
            """
            attribute_dict: dict[str, Any] = {}
            node_schema = node._schema
            parsed_attrs = self._parse_attrs(attrs)
            # Shared across this node's attributes so an inherited-attribute refetch
            # of the node happens at most once (see _resolve_schema_attribute).
            refetch_cache: dict[str, Any] = {}

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
                    attribute_dict[root_attr] = self._resolve_schema_attribute(
                        node, root_attr, node_attr, refetch_cache, refill
                    )

                # Handle relationships
                elif root_attr in node_schema.relationship_names:
                    if isinstance(node_attr, RelationshipManagerSync):
                        peers = self._resolve_many_relationship(node_attr, nested_attrs, has_nested, schemas, refill)
                        if peers:
                            attribute_dict[root_attr] = peers
                    elif isinstance(node_attr, RelatedNodeSync):
                        result = self._resolve_one_relationship(node_attr, nested_attrs, has_nested, schemas, refill)
                        if result is not None:
                            attribute_dict[root_attr] = result

            if include_id:
                attribute_dict["id"] = node.id

            return attribute_dict

    @dataclass
    class HostFetch:
        """Host nodes plus the schema and projection context needed to resolve them.

        Filled in as each requested kind is fetched, so the collections are mutable
        and start empty.
        """

        nodes: list[InfrahubNodeSync] = field(default_factory=list)
        schemas: dict[str, Any] = field(default_factory=dict)
        attrs_by_kind: dict[str, list[str]] = field(default_factory=dict)
        projections: dict[str, NodeProjection] = field(default_factory=dict)
        # Kinds that could not be fetched, and why. A kind that returned no nodes is
        # not a failure -- it answered, the answer was empty.
        failures: dict[str, str] = field(default_factory=dict)

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
            if not nodes:
                return None

            # Snapshot rather than read the running total: the counter belongs to the
            # client, which outlives a single call. Reporting the absolute value would
            # attribute an earlier run's requests to this one.
            requests_before = request_count(self.client)

            fetched = self._fetch_host_nodes(nodes=nodes, prefetch_relationships=prefetch_relationships)
            if not fetched.nodes:
                if fetched.failures:
                    # Nothing was fetched AND something went wrong. Returning an empty
                    # result here is indistinguishable from "the query matched nothing",
                    # so a transient API error would look like an empty inventory and a
                    # playbook would quietly no-op against zero hosts. Fail loudly instead.
                    detail = "; ".join(f"{kind}: {why}" for kind, why in sorted(fetched.failures.items()))
                    raise RuntimeError(f"No nodes could be fetched. Failures -- {detail}")
                # Every requested kind answered, and the answer was empty.
                return None

            warmer = PeerWarmer(
                fetch=self.client.fetch_nodes,
                store=self.client.client.store,
                # One id short of a full page. The SDK's non-parallel pager only stops
                # once `count - (offset + pagination_size)` goes negative, so a chunk of
                # exactly `pagination_size` costs a second, empty round-trip.
                page_size=max(1, self.client.client.pagination_size - 1),
                on_error=lambda kind, exc: self._handle_display(
                    exception=exc,
                    message=f"Failed to fetch peers for kind '{kind}'",
                    level="WARNING",
                ),
                order=Order(disable=True),
            )
            peer_batches = self._warm_peers(warmer=warmer, fetched=fetched)

            # `refill` collects nodes whose attributes the query never carried rather than
            # refetching them one by one. Anything it finds is loaded in one batched pass,
            # after which a second resolve reads the refreshed nodes back. Peers the
            # warmer already loaded in full are exempt: a value still empty after a
            # complete fetch is a genuine null, and queueing it would buy a redundant
            # refetch plus a second full resolution pass on every run.
            refill = RefillLedger(projections=fetched.projections, already_loaded=warmer.loaded)
            host_node_attributes = self._resolve_hosts(fetched=fetched, include_id=include_id, refill=refill)

            if refill:
                self._handle_display(
                    message=f"Refilling nodes with unqueried attributes: {dict.fromkeys(refill.pending)}",
                    level="DEBUG",
                )
                peer_batches += warmer.warm(refill.pending)
                host_node_attributes = self._resolve_hosts(
                    fetched=fetched, include_id=include_id, refill=RefillLedger.disabled(), refreshed=True
                )

            self._report_run_cost(
                requests_before=requests_before,
                peer_batches=peer_batches,
                peers_loaded=len(warmer.loaded),
                fetched=fetched,
                warmer=warmer,
            )

            return host_node_attributes

        def _report_run_cost(
            self,
            requests_before: int | None,
            peer_batches: int,
            peers_loaded: int,
            fetched: HostFetch,
            warmer: PeerWarmer,
        ) -> None:
            """State what the run cost, at raised verbosity only.

            The point is that the next report of slowness arrives as a number rather
            than an anecdote. It is deliberately not printed at default verbosity: an
            inventory run's output belongs to the playbook, not to diagnostics.

            The request count covers every HTTP round-trip, schema lookups included --
            those are not GraphQL queries but they cost the server the same. When no
            counter is attached (a wrapper built through ``__new__``, as the tests do)
            the peer figures are still worth reporting on their own.

            At ``-vvv`` the totals are followed by the breakdown behind them: what each
            requested kind cost and how far its query was narrowed, and what each peer
            kind cost. A total that looks wrong is only actionable once you can see
            which kind produced it.

            Parameters:
                requests_before (int | None): counter reading taken before this run began,
                    so the figure reported is this run's cost and not the client's lifetime total.
                peer_batches (int): how many batched peer fetches were issued.
                peers_loaded (int): how many related nodes came back.
                fetched (HostFetch): the host nodes and their projections, for the per-kind lines.
                warmer (PeerWarmer): carries the per-peer-kind tallies.
            """
            requests_now = request_count(self.client)
            unavailable = requests_before is None or requests_now is None
            cost = "unavailable" if unavailable else f"{requests_now - requests_before} request(s)"
            self._handle_display(
                message=(
                    f"Inventory fetch cost: {cost} to Infrahub, "
                    f"{peers_loaded} related node(s) loaded in {peer_batches} batch(es)"
                ),
                level="INFO",
            )
            for line in self._run_cost_breakdown(fetched=fetched, warmer=warmer):
                self._handle_display(message=line, level="VVV")

        @staticmethod
        def _run_cost_breakdown(fetched: HostFetch, warmer: PeerWarmer) -> list[str]:
            """The per-kind detail behind the run-cost totals.

            Separate from the emitting method so it can be asserted on directly, and so
            nothing here can raise into a run: this is a diagnostic, and a diagnostic
            that breaks the thing it reports on is worse than no diagnostic.
            """
            lines: list[str] = []

            hosts_by_kind: dict[str, int] = {}
            for node in fetched.nodes:
                kind = getattr(getattr(node, "_schema", None), "kind", "unknown")
                hosts_by_kind[kind] = hosts_by_kind.get(kind, 0) + 1

            for kind in sorted(hosts_by_kind):
                projection = fetched.projections.get(kind)
                if projection is None:
                    # A concrete kind a generic answered with: it has no projection of
                    # its own, and saying "not narrowed" would be a lie.
                    detail = "answered via a requested generic"
                elif not projection.narrowed:
                    detail = "no include given, full attribute set requested"
                else:
                    requested = ", ".join(sorted(projection.roots)) or "none"
                    excluded = len(projection.exclude or ())
                    detail = f"requested [{requested}], {excluded} field(s) excluded"
                lines.append(f"  host kind {kind}: {hosts_by_kind[kind]} node(s), {detail}")

            for kind in sorted(warmer.stats):
                stat = warmer.stats[kind]
                detail = f"{stat['requested']} id(s) referenced, {stat['batches']} batch(es), {stat['loaded']} loaded"
                if stat["failed"]:
                    detail += f", {stat['failed']} batch(es) failed"
                lines.append(f"  peer kind {kind}: {detail}")

            if not lines:
                return []
            return ["Inventory fetch cost, by kind:", *lines]

        def _fetch_host_nodes(self, nodes: dict[str, Any], prefetch_relationships: bool | None) -> HostFetch:
            """Fetch every requested kind, narrowed to what the user actually asked for.

            Parameters:
                nodes (dict[str, Any]): A dictionary of node kinds to fetch.
                prefetch_relationships (bool, optional): Whether to prefetch relationships.

            Returns:
                HostFetch: the host nodes plus the schema and projection context to resolve them.
            """
            fetched = HostFetch()
            order = Order(disable=True)

            for node_kind in nodes:
                # `raise_when_missing=False` makes an unknown kind return None here
                # regardless of whether the wrapper's exception decorator is installed.
                # Relying on the decorator alone is not enough: it is attached in
                # __init__, so any caller that builds the wrapper another way gets the
                # raw SchemaNotFoundError instead.
                node_schema = self.client.fetch_single_schema(kind=node_kind, raise_when_missing=False)
                if node_schema is None:
                    # An unknown kind -- a typo, or a kind that does not exist on this
                    # branch. Skip it the way a failed fetch is skipped: reading
                    # attribute_names off None would abort the whole inventory over one
                    # bad entry. It can also mean the lookup itself failed and the
                    # wrapper's decorator swallowed it (server unreachable, bad token),
                    # which is why the wording does not promise the kind is unknown.
                    self._handle_display(
                        message=f"No schema available for kind '{node_kind}', skipping it",
                        level="WARNING",
                    )
                    fetched.failures[node_kind] = "no schema found, or the schema lookup failed"
                    continue
                fetched.schemas[node_kind] = node_schema
                node_options = nodes.get(node_kind) or {}
                exclude = node_options.get("exclude", None)

                # `include` is not a projection as far as the SDK is concerned: it only
                # opts cardinality-many relationships into the query, and a dotted path
                # matches nothing at all. NodeProjection turns the user's spec into the
                # arguments that do narrow it -- the exclude complement plus the
                # relationship opt-ins -- so an explicit request stops paying for the
                # whole node on every page.
                projection = NodeProjection.build(
                    schema=fetched.schemas[node_kind],
                    include=node_options.get("include", None),
                    exclude=exclude,
                    resolvable_attrs=self.get_attributes_for_schema(schema=fetched.schemas[node_kind], exclude=exclude),
                )
                try:
                    nodes_from_kind = self.client.fetch_nodes(
                        kind=node_kind,
                        include=projection.include,
                        exclude=projection.exclude,
                        filters=node_options.get("filters", None),
                        prefetch_relationships=prefetch_relationships,
                        order=order,
                    )
                except Exception as exc:
                    self._handle_display(
                        exception=exc,
                        message=f"Failed to fetch_nodes for kind '{node_kind}'",
                        level="WARNING",
                    )
                    fetched.failures[node_kind] = str(exc) or type(exc).__name__
                    continue

                if nodes_from_kind is None:
                    # `None` is not an empty result: the wrapper's exception decorator
                    # logs the failure and returns nothing rather than raising whenever a
                    # Display is attached -- which it always is in the inventory. Without
                    # this the `except` above never fires there, `failures` stays empty,
                    # and a broken fetch is indistinguishable from a kind that legitimately
                    # matched nothing: the run hands Ansible zero hosts and reports success.
                    fetched.failures[node_kind] = "fetch failed, see the warning above"
                    continue

                if not nodes_from_kind:
                    continue
                fetched.attrs_by_kind[node_kind] = projection.attrs
                fetched.projections[node_kind] = projection
                # A generic kind answers with nodes of its concrete kinds, and resolution
                # looks the attribute list up by the node's own kind -- so register those
                # too, or `nodes: {SomeGeneric: {}}` dies on a KeyError in `_resolve_hosts`
                # and warms no peers. `setdefault` so an explicitly requested kind keeps
                # its own spec.
                for fetched_node in nodes_from_kind:
                    fetched.attrs_by_kind.setdefault(fetched_node._schema.kind, projection.attrs)
                fetched.nodes.extend(nodes_from_kind)

            return fetched

        def _warm_peers(self, warmer: PeerWarmer, fetched: HostFetch) -> int:
            """Load the peers that nested paths are about to read.

            Only ids the host nodes reference are fetched, and only where the inline peer
            payload came back short, so this costs one request per page of peers rather
            than one pass over every peer kind in the database.

            Returns:
                int: how many peer batches were issued.
            """
            referenced = warmer.collect(nodes=fetched.nodes, attrs_by_kind=fetched.attrs_by_kind)
            if not referenced:
                return 0

            self._handle_display(
                message=f"Loading referenced peers: {dict.fromkeys(referenced)}",
                level="DEBUG",
            )
            # No schema fetch for the peer kinds: `resolve_node_mapping` reads a node's
            # own `_schema`, never the `schemas` mapping it is handed, so loading them
            # here would be a round-trip nothing reads back.
            return warmer.warm(referenced)

        def _resolve_hosts(
            self,
            fetched: HostFetch,
            include_id: bool,
            refill: RefillLedger,
            refreshed: bool = False,
        ) -> dict[str, Any]:
            """Resolve every host node exactly once against the warmed store.

            Parameters:
                fetched (HostFetch): the host nodes and their resolution context.
                include_id (bool): Whether to include the node ID in each result.
                refill (RefillLedger): where to record attributes the query never carried.
                refreshed (bool): read each node back from the store first. A refill
                    replaces the node in the store rather than mutating the instance in
                    hand, so the second pass has to look it up again.
            """
            store = self.client.client.store
            resolved: dict[str, Any] = {}

            for host_node in fetched.nodes:
                node = (store.get(key=host_node.id, raise_when_missing=False) or host_node) if refreshed else host_node
                result = self.resolve_node_mapping(
                    node=node,
                    attrs=fetched.attrs_by_kind[host_node._schema.kind],
                    schemas=fetched.schemas,
                    include_id=include_id,
                    refill=refill,
                )
                self._handle_display(
                    message=f"Resolved attributes for node '{get_node_identifier(host_node)}'",
                    level="DEBUG",
                )
                if result:
                    resolved[str(host_node)] = result

            return resolved

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
                # Unwrap nested {"value": ...} dicts used by Ansible data format
                if isinstance(value, dict) and "value" in value:
                    value = value["value"]
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
                return None

            include = [key for key in data if key not in ("id", "hfid")] or None
            try:
                node = self.client.fetch_single_node(
                    kind=kind, id=node_id, hfid=node_hfid, include=include, raise_when_missing=False
                )
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
                    attr_value = data.get(attr_name)
                    # Unwrap {"value": ...} dicts from Ansible data format —
                    # setattr on SDK node attributes expects the raw value.
                    if isinstance(attr_value, dict) and "value" in attr_value:
                        attr_value = attr_value["value"]
                    setattr(
                        self.infrahub_node,
                        attr_name,
                        attr_value,
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

    def get_node_identifier(_node) -> str:  # type: ignore[misc]
        return "unknown"

    class InfrahubclientWrapper:
        pass

    class InfrahubNodesProcessor:
        pass

    class InfrahubQueryProcessor:
        pass

    class InfrahubModule:
        pass
