# Feature Specification: Dynamic Inventory Fetch Performance

**Feature Branch**: `001-inventory-fetch-performance`

**Created**: 2026-08-23

**Status**: Draft (retroactive — every requirement below describes delivered, verified work)

**Input**: User description: "those performances improvements"

## Clarifications

### Session 2026-08-23

- Q: When a related node that a host references fails to load, what happens to that host? → A: The host is still produced with the affected attribute empty, a warning names the related type that failed, and the run succeeds.
- Q: Does a run report what it cost, so the next slowness report arrives with a number? → A: Yes, at raised verbosity only — a run states how many queries it sent and how many related nodes it loaded; silent at default verbosity.
- Q: How far do the performance criteria have to hold — is there a stated host-count ceiling? → A: No ceiling. The guarantee is the shape (FR-001, SC-004); wall-clock claims stay scoped to the measured estate, because elapsed time depends on the related nodes requested and on the health of the Infrahub instance, not on host count alone.
- Q: Which vocabulary is canonical for the thing a definition selects? → A: The inventory definition's own — **node**, **node type**, **related node** — with **host** reserved for the Ansible inventory entry. Revisit if reserved-variable-name warnings force a renaming.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A large estate builds in seconds, not minutes (Priority: P1)

An automation engineer runs a playbook against an Infrahub instance holding several hundred hosts.
Their inventory definition asks for a handful of attributes on each host plus a few attributes that
live on related nodes (a site name, an address, an owner). Today they wait long enough that the
inventory step dominates the playbook run, and long enough that it sometimes times out. They want the
inventory to be ready in seconds, and they want exactly the same hosts and variables they got before.

**Why this priority**: This is the reported problem. Everything else in this specification is either a
prerequisite for it or a correctness guarantee that stops it from being bought with wrong data. A fast
inventory that returns different variables is a regression, not an improvement.

**Independent Test**: Point the inventory at an estate of several hundred hosts, using a definition
that reaches into related nodes. Measure wall-clock time and count the queries sent to Infrahub.
Compare the produced inventory against the previous behaviour for the same definition — it must match
exactly.

**Acceptance Scenarios**:

1. **Given** an estate of roughly 650 hosts and a definition that requests attributes on related nodes, **When** the inventory is built, **Then** it completes in under 10 seconds and returns the same hosts and host variables as the previous behaviour.
2. **Given** the same estate, **When** the inventory is built, **Then** the number of queries sent to Infrahub is a small constant, not proportional to the number of hosts.
3. **Given** an estate twice the size, **When** the inventory is built, **Then** the query count grows with the number of pages of data, not with the number of hosts.

---

### User Story 2 - Asking for less costs less (Priority: P2)

An engineer only needs two attributes per host. They say so in their inventory definition. They expect
the system to ask Infrahub for those two attributes and nothing else, so the run is cheaper for them
and lighter on the server they share with everyone else.

**Why this priority**: Independent of P1 and separately valuable — it reduces load on the Infrahub
instance itself, not just the client's wait. It is second because an estate that is slow with a narrow
definition is still slow with a wide one; P1 has to hold regardless of what was requested.

**Independent Test**: Build the same inventory twice, once with a narrow attribute selection and once
with none, and compare the amount of data transferred. The narrow run must transfer measurably less.

**Acceptance Scenarios**:

1. **Given** a definition naming a small set of attributes, **When** the inventory is built, **Then** only those attributes (plus the identifiers every host needs) are requested from Infrahub.
2. **Given** a definition naming no attributes at all, **When** the inventory is built, **Then** the full previous set of attributes is still returned, unchanged.
3. **Given** a definition that asks only for the identifier of a related node, **When** the inventory is built, **Then** that related node is never fetched.

---

### User Story 3 - Attributes on related nodes always arrive (Priority: P3)

An engineer's hosts point at a site, and the relationship is declared in terms of a broad, shared type
("a location") while the attribute they want lives on the specific type ("a site's name"). They expect
to get the site name. Today they do — but only because the system quietly re-asks for every host that
looked incomplete, which is the single largest source of the slowness in P1.

**Why this priority**: This is the shape that makes P1 hard. It is listed separately because it is the
correctness guarantee that must survive the optimisation: if the expensive re-asking is removed without
replacing it, these values silently become empty. It is the most common relationship shape in real
schemas.

**Independent Test**: Model a relationship whose declared type does not expose the attribute being
requested, then request that attribute. It must resolve to the real value, and the run must stay within
its query budget.

**Acceptance Scenarios**:

1. **Given** a relationship declared through a broad type and an attribute that exists only on the specific type, **When** the inventory is built, **Then** the attribute resolves to its real value.
2. **Given** that same definition, **When** the inventory is built, **Then** it costs a bounded number of queries rather than one per related node.
3. **Given** an attribute whose real value is genuinely empty, **When** the inventory is built, **Then** the empty value is accepted as the answer and no further query is made for that host.

---

### User Story 4 - Cached inventories do not collide (Priority: P4)

An engineer works across two branches of their data, and keeps two inventory definitions pointed at the
same Infrahub instance — one selecting devices, one selecting addresses. With caching enabled, each
combination must have its own cache entry. Today they can see one definition's results served to the
other.

**Why this priority**: A correctness bug that only bites users who have enabled caching, and produces
confusing rather than catastrophic results. Real, but narrower in blast radius than P1-P3.

**Independent Test**: Build cache identities for definitions that differ only by branch, and only by
selected node types, and confirm all of them differ.

**Acceptance Scenarios**:

1. **Given** two definitions identical except for the branch, **When** both are cached, **Then** they occupy separate cache entries.
2. **Given** two definitions identical except for the node types selected, **When** both are cached, **Then** they occupy separate cache entries.
3. **Given** a run served entirely from cache, **When** it completes, **Then** it does not rewrite the cache entry it just read.
4. **Given** a cache written by an older version whose stored shape differs, **When** a newer version runs, **Then** the stale entry is not reused.

---

### User Story 5 - A failed fetch says so (Priority: P5)

An engineer mistypes a node type, or points at a branch where it does not exist. If some node types
still resolve, they want the rest of the inventory. If nothing resolves because everything failed, they
want to be told why — not handed an empty inventory that looks like a legitimately empty estate.

**Why this priority**: Diagnosability rather than performance, but it shares the same code path and the
same failure surface, and silent-empty is the failure mode most likely to waste an engineer's afternoon.

**Independent Test**: Run one definition with a valid type and an invalid one, and another with only
invalid types. The first must return the valid hosts; the second must raise, naming what failed.

**Acceptance Scenarios**:

1. **Given** a definition naming one valid and one unknown node type, **When** the inventory is built, **Then** the unknown type is skipped and the valid one still resolves.
2. **Given** a definition where every named type fails, **When** the inventory is built, **Then** the run fails with a message naming each type and the reason it failed.
3. **Given** a definition where every named type is valid but genuinely holds no nodes, **When** the inventory is built, **Then** the run succeeds with no hosts and no error.
4. **Given** a run in which a batch of related nodes fails to load, **When** the inventory is built, **Then** a warning names the related type that failed, every host that referenced it is still produced with the affected attributes empty, and the run succeeds.

### Edge Cases

- An attribute whose real value is `false`, `0`, or an empty string is a present value, not a missing one, and must not be treated as a reason to ask again.
- More related nodes are referenced than fit in a single page of results — the batch must be split, and every page must be retrieved.
- A batch of related nodes comes back partially, or fails outright: only the nodes that actually arrived may be treated as retrieved, and hosts referencing the ones that did not arrive are still produced with those attributes left empty.
- Two different node types are selected in one definition, each with its own attribute selection.
- An attribute is requested two levels deep (a host's related node's own related node).
- The same related node is referenced by many hosts — it must be fetched once, not once per referring host.
- A node type named in the definition does not exist on the selected branch.
- The Infrahub instance is slow enough under load that a short client timeout aborts an otherwise-successful run.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The number of queries a single inventory run sends to Infrahub MUST be determined by the number of node types selected, the number of pages of results, and the number of distinct related-node types referenced — and MUST NOT grow with the number of hosts.
- **FR-002**: An attribute that resolves to an empty or absent value MUST NOT cause the system to re-request the host that owns it.
- **FR-003**: When a definition names the attributes it wants, the system MUST request only those attributes from Infrahub, together with the identifiers every host requires.
- **FR-004**: When a definition names no attributes, the system MUST return the same full set of attributes it returned previously.
- **FR-005**: Related nodes MUST be retrieved in batches, grouped by type, containing only the nodes actually referenced by the hosts in this run.
- **FR-006**: A batch of related nodes MUST be split so that no single request asks for more nodes than one page of results can return, and every resulting page MUST be retrieved.
- **FR-007**: A related node whose requested attributes are already available MUST NOT be retrieved again.
- **FR-008**: A related node that has already been retrieved in this run MUST NOT be retrieved again, and only nodes that actually came back may be recorded as retrieved.
- **FR-009**: An attribute of a related node MUST resolve to its real value even when the relationship is declared in terms of a broader type that does not expose that attribute.
- **FR-010**: When a definition requests only the identifier of a related node, the system MUST NOT retrieve that node.
- **FR-011**: Cache entries MUST be distinguished by the Infrahub address, the branch, and the set of node types and attributes requested.
- **FR-012**: Cache entries MUST carry a version of the stored shape, and entries written under an earlier version MUST NOT be reused.
- **FR-013**: The cache MUST be written only when the run actually fetched from Infrahub.
- **FR-014**: A node type that cannot be found MUST be skipped, and the remaining node types MUST still resolve.
- **FR-015**: When a run retrieves no hosts at all and at least one node type failed, the run MUST fail with a message naming each failed type and its reason.
- **FR-016**: When a run retrieves no hosts and no node type failed, the run MUST succeed and produce no hosts.
- **FR-017**: The default request timeout MUST be at least 60 seconds, so that a large estate under load is served rather than aborted mid-run.
- **FR-018**: For any given definition, the hosts and host variables produced MUST be identical to those produced before these changes.
- **FR-019**: When related nodes of a given type fail to load, the run MUST emit a warning naming that type, MUST still produce every host that referenced them with the affected attributes left empty, and MUST NOT fail on that account.
- **FR-020**: At raised verbosity, a run MUST report how many requests it sent to Infrahub and how many related nodes it loaded. At default verbosity it MUST report neither. The request figure counts every HTTP round-trip, schema lookups included, so it is legitimately higher than a GraphQL-only count.

### Key Entities

- **Node**: An entry in Infrahub — a device, an address, a site. Carries attributes and relationships to other nodes. This is the Infrahub sense of the word, not Ansible's: a node becomes a host only if a definition selects its node type.
- **Host**: An entry in the inventory Ansible acts on, built from one node. The spec keeps *host* and *node* distinct throughout: hosts are what Ansible sees, nodes are what is fetched.
- **Node type**: The named type of node a definition selects (devices, addresses, sites). Written as a key under `nodes:` in the inventory definition; Infrahub itself calls this a *kind*. One definition may select several, each with its own attribute selection.
- **Attribute selection**: The list of attributes a definition asks for, which may reach through relationships (a host's site's name). Determines both what is returned and what may be requested.
- **Related node**: A node referenced by another node through a relationship, whose attributes may be needed to build a host's variables. May be referenced by many hosts.
- **Cache entry**: A stored inventory result, identified by the address, branch, selection, and stored shape it was built from.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Building an inventory of roughly 650 hosts with attributes reached through relationships completes in under 10 seconds, down from over 100 seconds.
- **SC-002**: That same run sends at least 95% fewer queries to Infrahub than it did before.
- **SC-003**: That same run transfers at least 50% less data than it did before.
- **SC-004**: Doubling the number of hosts in a run does not double the number of queries sent to Infrahub.
- **SC-005**: For a representative set of definitions — no attribute selection, a narrow selection, several node types, and a two-level selection — the inventory produced is identical to the inventory produced before these changes.
- **SC-006**: Every requested attribute that has a value in Infrahub is present in the produced inventory, including attributes reached through a relationship declared in terms of a broader type.
- **SC-007**: A run in which every selected node type fails reports an error naming each failure, and never returns an empty inventory silently.
- **SC-008**: Two runs that differ only in branch, or only in the node types selected, never serve each other's cached results.
- **SC-009**: A slowness report from the field can be quantified from a raised-verbosity run alone, without attaching an instrumented harness: the run states its own query count and how many related nodes it loaded.

## Out of Scope

- Exposing or tuning the page size and concurrency settings used when talking to Infrahub. These were measured and did not help: raising the page size cut the query count but did not reduce wall-clock time. They remain at their defaults.
- Any change to Infrahub itself, or to how it answers queries.
- Any change to the lookup plugin or to the modules that create and update nodes.
- Any new user-facing configuration option. The improvement must apply to existing inventory definitions with no edits.
- Concurrent or asynchronous fetching within a single run.

## Assumptions

- "Slowness" as reported means the wall-clock time to build an inventory, and the load that building it places on the shared Infrahub instance. Both are treated as in scope.
- The measurements quoted in Success Criteria come from a production-shaped instance of roughly 650 hosts, using definitions that reach attributes through relationships — the shape the reports came from.
- Existing inventory definitions must keep working unchanged. Identical output is a hard requirement, not a goal; a faster run that returns different variables is a regression.
- Users may or may not have caching enabled. The cache correctness requirements apply only when they do, and no behaviour change is expected for users who do not.
- The Infrahub instance being queried supports retrieving several nodes of one type by identifier in a single request. Without that, batching related nodes is not possible.
- Raising the default timeout is a safety net for large estates, not a performance measure; runs are expected to finish well inside it.
- Wall-clock time is not a function of host count alone. It also depends on how many related nodes a definition reaches into, how many distinct types those span, and the health and load of the Infrahub instance answering. The measured figures in SC-001 to SC-003 therefore describe one real estate rather than a promise that scales; SC-004 and FR-001 carry the part that generalises.
- No maximum estate size is specified. A definition that stays within the cost shape of FR-001 is expected to keep working as the estate grows, but no wall-clock figure is claimed beyond what was measured.
- Attribute names reaching the inventory as host variables can collide with names Ansible reserves, which produces a warning at run time. That is a pre-existing condition of the plugin, untouched by this work and out of scope here, but it is the one thing likely to force the naming settled above to be revisited.
