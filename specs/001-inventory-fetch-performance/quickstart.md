# Quickstart: Verifying Dynamic Inventory Fetch Performance

How to reproduce the claims in the spec, and what to run before touching this code.

## Verify correctness

```bash
invoke format && invoke lint          # autoflake + ruff (check + format) + mypy + yamllint + rumdl
invoke tests-sanity                   # ansible-test sanity, Docker
invoke tests-unit                     # 106 unit tests
```

`invoke lint` runs mypy as of #378; it used to not, and running it separately was a step this feature
needed. A failing `ruff check` still masks the steps after it, so read the whole output.

## Verify the round-trip budgets

Integration tests need Docker and the `integration` dependency group.

```bash
uv sync --group integration
export INFRAHUB_TESTING_IMAGE_VER=1.9.9

# nightly and on dispatch: correctness plus a gross-regression counter
uv run --group integration pytest tests/integration/processor -m integration

# Scheduled only: per-shape measured budgets, prints its own totals
uv run --no-default-groups --group integration pytest \
  tests/integration/processor/test_fetch_roundtrip_measurement.py \
  -m integration -p no:pytest-infrahub-performance-test -s -v
```

The measurement budgets are **measured, not derived**. They depend on SDK pagination behaviour the
collection does not control, so an `infrahub-sdk` or Infrahub image bump can legitimately shift one by
±1 with no change under `plugins/`. If one fails after a dependency bump and nothing in `plugins/`
changed, re-measure with `-s` and move the number, recording the versions. A rise *with* `plugins/`
changes is a regression.

## Reproduce the headline numbers

Against a real estate (the reported numbers came from ~652 devices):

```bash
export INFRAHUB_ADDRESS=https://your-instance
export INFRAHUB_API_TOKEN=<token>
time ansible-inventory -i your.infrahub.yml --list > /dev/null
```

To A/B against the previous behaviour, use `git worktree`, not `git stash` — `uv run` re-dirties
`uv.lock`, which blocks stash pops and can silently block a `git checkout`, leaving you measuring the
branch you thought you had left.

| Shape | Before | After |
|---|---|---|
| Default, no `include` | 700 requests / 3758 KB / 102.71s | 15 / 1555 KB / 3.23s |
| Narrow `include` | 146 requests / 1673 KB / 22.08s | 18 requests |
| Two node types (1508 hosts) | 381 requests / 3027 KB / 50.72s | 37 requests |
| Nested depth-2 | 144 requests / 1648 KB / 20.72s | 18 requests |

Output was byte-identical to the previous behaviour in all four.

## Things that look like improvements and are not

- **Raising `pagination_size`.** 50 → 500 cut requests 20 → 4 and moved wall-clock 7.10s → 7.60s.
  Recorded in the spec's Out of Scope.
- **Deleting the per-node refetch.** It looks like dead code. It fired 653 times on a 652-device estate
  and was the only thing resolving attributes through generic peers. See `research.md` R4.

## Where the last requirement landed

FR-020 / SC-009 — a run reporting its own cost at raised verbosity — ships in PR #381, built to the
design in `research.md` R1: a counting `Recorder` passed as `Config.custom_recorder` from
`InfrahubclientWrapper`. `fetch_and_process` emits the totals at `-v` and the by-kind breakdown behind
them at `-vvv`.
