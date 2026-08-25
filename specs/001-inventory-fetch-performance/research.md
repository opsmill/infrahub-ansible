# Phase 0 Research: Dynamic Inventory Fetch Performance

Only one item in this feature carried an unresolved design question. The other nineteen requirements
describe delivered code whose decisions were made against measurements rather than research; those are
recorded here too, briefly, because the measurements are the reason the obvious alternatives were
rejected and re-proposing them later would waste a cycle.

## R1 — How a run counts the queries it sent (FR-020, SC-009)

**Question**: FR-020 requires a run to report how many queries it sent to Infrahub. The wrapper cannot
see that number: the SDK paginates inside `client.filters()`, one level below `InfrahubclientWrapper`,
so a wrapper-level counter reports fetch *operations* and misses exactly the thing that varies — pages.

**Decision**: Implement a counting recorder and pass it as `custom_recorder` when the wrapper builds its
`Config`.

The SDK exposes a first-class, runtime-checkable `Recorder` protocol — a single method
`record(response: httpx.Response) -> None` — invoked from `InfrahubClientSync._record` on every HTTP
response (`infrahub_sdk/client.py:235`, called at four request sites including the sync `_request` at
`:3788`). `Config` already accepts `custom_recorder`, and the wrapper already constructs `Config` at two
sites (`infrahub_utils.py:125` and `:136`), so the wiring is a keyword argument in code the wrapper
already owns.

**Rationale**:

- It counts at the true HTTP boundary, below pagination, so the number reported is the number a network
  trace would show. That is the number the field reports need.
- It is a supported extension point, not a monkeypatch. Nothing is reassigned on the client at runtime.
- It keeps Principle IV intact: the wrapper stays the single place that constructs and configures the
  SDK client.
- The counter itself needs no SDK import at runtime — only an annotation, which goes under
  `TYPE_CHECKING`, exactly as `peers.py` already does for `Callable`. The `HAS_INFRAHUBCLIENT` guard is
  unaffected.

**Alternatives considered**:

- *Wrap `client.execute_graphql` at runtime, as the tests do.* Accurate, and already proven in
  `count_graphql` in the integration tests — but reassigning an attribute on the SDK client in
  production code is a monkeypatch in a place where a supported hook exists. Fine for a test harness,
  wrong for shipped code.
- *Count wrapper-level fetch operations only.* Needs no SDK cooperation at all, but under-reports by
  precisely the amount that matters. A run that sent 15 requests would report 3.
- *`Config.echo_graphql_queries`.* The SDK can print every query it sends. That is a debugging firehose
  on stdout, not a count, and it cannot be gated behind Ansible's verbosity.

**Sub-question resolved during implementation (T033)**: the count is reported **once per run**, not per
node type.

This turned out to be settled by fact rather than preference. The recorder is handed an
`httpx.Response` and nothing else — there is no node type to attribute a response to at that layer, and
the SDK does not carry one through. Per-type attribution would need a second, different mechanism
sitting above the wrapper, which would then be counting fetch operations again and miss pagination —
the exact failure mode this decision existed to avoid.

What the processor *does* know is attributed and reported alongside: how many related nodes were loaded
and how many batches it took. So the emitted line is one total request count plus two figures the
inventory code owns:

```text
Inventory fetch cost: 15 request(s) to Infrahub, 41 node(s) loaded in 2 batch(es)
```

**Consequence worth stating**: the request count covers *every* HTTP round-trip, schema lookups
included. Those are REST calls, not GraphQL queries, so this figure is legitimately higher than what the
tests' `count_graphql` helper reports. The integration test asserts `reported >= graphql_calls` rather
than equality for exactly this reason.

## R2 — Why the peer fetch is batched by id rather than prefetched by type

**Decision**: Fetch related nodes with a filter on the ids actually referenced, chunked by page size.

**Rationale**: The original design fetched a whole related type at once on the reasoning — correct in
2023 — that one large call beats several small ones. That holds only while the type is small. It makes
cost track the size of the database rather than the size of the inventory, which is precisely the
reported failure. Batching by referenced id keeps the "one call per type" shape but bounds what the call
returns.

**Alternatives considered**: raising `pagination_size` so fewer, larger pages are needed. Measured:
50 → 500 cut the request count from 20 to 4 but moved wall-clock the wrong way, 7.10s → 7.60s. Rejected,
and recorded in the spec's Out of Scope so it is not re-proposed.

## R3 — Why chunks are one id short of a page

**Decision**: Chunk peer ids at `pagination_size - 1`.

**Rationale**: The SDK's non-parallel pager stops only once `count - (offset + pagination_size)` goes
negative. A chunk of exactly `pagination_size` therefore costs a second, empty round-trip. One id short
avoids it. This is SDK behaviour the collection does not control, which is why the integration budgets
are documented as measured-against-a-version rather than derived.

## R4 — Why the per-node refetch could not simply be deleted

**Decision**: Replace it with a bounded refill pass rather than remove it.

**Rationale**: The refetch looked like dead code and was assumed to be. It was not: on a 652-device
estate it fired 653 times. It was the only mechanism making an attribute resolve when a relationship
declares a *generic* peer — the SDK builds a relationship's inline payload from the **declared** peer
schema, so an attribute that exists only on the concrete type is never requested and never arrives.
Deleting it would have made those attributes silently empty. The replacement records what was missing
during resolution, loads it in one batched pass, then resolves again.

**Alternatives considered**: asking the SDK to project the concrete peer schema. Rejected for this
feature — it is an SDK change, not a collection change, and the user explicitly declined to open it.

## R5 — Why `include` had to be translated rather than passed through

**Decision**: Convert the user's `include` list into the `exclude` complement the SDK honours.

**Rationale**: Verified by rendering the query both ways: with and without `include`, the SDK produced
byte-identical 1576-character queries. `include` does not narrow anything — it only opts
cardinality-many relationships in. Only `exclude` narrows. So a user writing `include: [name]` was
paying for every attribute on the type. The projection computes the complement of what was asked for and
passes that as `exclude`.
