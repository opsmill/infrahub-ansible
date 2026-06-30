# The gate model

- [Trust tiers](#trust-tiers-pattern-7-more-trust--more-layers) — T0/T1/T2 and when each applies
- [Hybrid judge policy](#hybrid-judge-policy) — ship gates (full P2) vs verify gates (lighter re-read)
- [Verify-gate procedure](#verify-gate-procedure-lighter) — step-by-step lighter checkpoint

## R-codes glossary

| Code | Meaning |
|---|---|
| **R1** | Independent verbatim criteria — the judge receives the original source (issue body, `.bug-analysis-<key>.md`, spec/PRD, or pre-fix CI log) fetched fresh, not a summary. |
| **R2** | Degrade-to-re-read — when no subagent can be dispatched, fall back to the lighter verify-gate procedure AND declare the judgment degraded. |
| **R3** | Canonical-copy requirement — `opsmill-dev/skills/quality-gates/` is the canonical copy and `opsmill-repo`'s is synced. A repo-maintenance rule, not a judge rule (see `DECISION.md` ADR-004); listed here only so the R-series numbering reads complete. |
| **R4** | Human-approval-as-judge — when a mandatory human-approval step already exists before the irreversible action, that approval IS the independent judgment; no subagent is dispatched. |

A **gate** has four properties:

1. **Pass definition** — an unambiguous statement of what "passes" means here.
2. **Independent verification** — judged by something other than the reasoning that produced
   the artifact.
3. **Required evidence** — the actual command output / artifact, pasted, not asserted (see P1).
4. **STOP-on-fail** — a failed gate halts the workflow; it never warns-and-continues.

## Trust tiers (Pattern 7: more trust → more layers)

| Tier | What the skill does | Required gates |
|---|---|---|
| **T0** | advisory / read-only output | P1 + self-review checklist |
| **T1** | mutates a branch, does not ship | P1 (P2 optional) |
| **T2** | ships / opens PR / merges / force-pushes / stamps a "complete" marker | P1 + P2 + P3 |

## Hybrid judge policy

Within T2, there are two checkpoint kinds:

- **Ship gate** (irreversible / outward-facing: open a PR, merge, force-push, stamp
  `AGENT_*_COMPLETE`, open drift PRs/issues, declare CI resolved) → run the **full independent
  judge** (`primitives/independent-judge.md`). T2 ship gates use **N=3 majority judging**: dispatch
  the judge 3 times independently; 2 or more FAILs → FAIL. On PASS, write the commit-bound receipt
  per `primitives/independent-judge.md` (Claude Code hook enforcement).
- **Verify gate** (intermediate / internal: confirm a test passes, run pre-CI checks, resolve
  mechanical conflicts before a push) → run the **lighter fresh-context re-read** (below). Verify
  gates use a **single judgment**.

### Verify-gate procedure (lighter)

1. Re-read the original criteria fresh — fetch it; do not rely on memory.
2. Check each pass criterion one by one.
3. Paste proving evidence for each criterion.
4. State PASS or FAIL.

This is stronger than a bare assertion and cheaper than a subagent; it is NOT a substitute for a
ship gate's full judge. A DEGRADED receipt records that this lighter procedure was used (no
subagent was available).

**Note:** the hook enforces receipt PRESENCE (any PASS or DEGRADED receipt for the current HEAD
unblocks the ship action); N=3 majority for T2 is prose discipline — it is not hook-verified.
