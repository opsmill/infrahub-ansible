---
name: quality-gates
description: >-
  Shared in-workflow quality gates for code/PR skills — the gate model, trust tiers, and the
  three primitives (evidence-before-done, independent judge, anti-gaming). DO NOT TRIGGER
  directly — referenced by consumer skills via relative path.
user-invocable: false
allowed-tools: [Read]
metadata:
  version: 0.1.0
  author: OpsMill
---

# Quality Gates

Shared reference for turning a skill's *critical* steps from prompts into **gates**: enforced
checkpoints with independent verification, required evidence, and a STOP-on-fail. Not invocable
directly; consumer skills reference these files by relative path.

This is the CANONICAL copy. `opsmill-repo/skills/quality-gates/` is a synced copy; if they
diverge, this copy wins (see `DECISION.md`).

## Contents

- `gates/gate-model.md` — the 4 properties of a gate, the 3 trust tiers, and the hybrid
  ship-vs-verify judge policy.
- `gates/primitives/evidence-before-done.md` — **P1**: no "done" claim without pasted output.
- `gates/primitives/independent-judge.md` — **P2**: author≠judge via a fresh subagent.
- `gates/primitives/anti-gaming.md` — **P3**: measure intent, not form; forbidden evasions.

## Trust tiers (summary)

| Tier | Skill does | Required gates |
|---|---|---|
| T0 | advisory / read-only | P1 + self-review |
| T1 | mutates a branch, no ship | P1 (P2 optional) |
| T2 | ships / opens PR / merges / force-pushes / stamps a "complete" marker | P1 + P2 + P3 |

## Consumer Gate Mapping

Which skills declare which gates. Keep this in sync as consumers are wired.

| Skill | Plugin | Tier | Ship gate (full P2)? |
|---|---|---|---|
| fixing-bugs | dev | T2 | yes — before `AGENT_FIX_COMPLETE` |
| test-driving-bugs | dev | T2 | yes — before `AGENT_TEST_COMPLETE` (local mode stamps the marker; PR mode also opens the draft PR; both require the ship gate) |
| pr | dev | T2 | yes — before `gh pr create` |
| monitoring-pull-requests | dev | T2 | yes — before declaring CI resolved |
| merging-branches | dev | T2 | yes — before opening the draft PR |
| rebase | dev | T1 escalating to T2 at force-push | yes — the ship gate is mandatory before force-push (T2); branch-only rebases without force-push are T1 |
| commit | dev | T1 | no |
| analyzing-bugs | dev | T0 | no |
| creating-issues | dev | T0 | no (human is judge, R4) |
| grilling-ideas | dev | T0 | no (human is judge, R4) |
| auditing-repo-standards | repo | T0 | no |
| auditing-agentic-structure | repo | T0/T1 | no |
| detecting-repo-drift | repo | T2 | yes — before opening each PR |

## Adding a new consumer

A new code/PR skill that ships output (opens a PR, merges, force-pushes, stamps a completion
marker) MUST declare a T2 ship gate. Propose any new primitive as an ADR in `DECISION.md`
rather than copying gate logic into the consumer.

## Hook enforcement (Claude Code only)

Under Claude Code, a `PreToolUse` hook (`hooks/ship-gate-check.sh`, registered in this plugin's `.claude-plugin/plugin.json`) enforces two deterministic gates on Bash commands — both **opt-in per repo** (`.claude/quality-gates/enabled`; the hook is a no-op until it exists) and both overridable with `QUALITY_GATES_BYPASS=1`:

- **Branch discipline:** denies `git commit` / `git push` while on a protected branch (`main`, `master`, `develop`, `stable`, `release/*`). Create a feature branch first.
- **Ship-gate receipt (commit-bound):** denies the irreversible ship actions — `gh pr create`/`merge`, `git push --force*`, and `AGENT_FIX_COMPLETE`/`AGENT_TEST_COMPLETE` marker stamps — unless a PASS/DEGRADED receipt exists for the current HEAD. The P2 judge writes `.claude/quality-gates/receipts/<HEAD>.json` on PASS; a new commit invalidates it.

Progressive enhancement: the prose gates are unchanged and remain the behaviour under Codex; the hook adds deterministic enforcement under Claude. Gitignore `.claude/quality-gates/receipts/` in consuming repos.

### Receipt format (ship-gate PASS)

On a ship-gate PASS the P2 judge writes a commit-bound receipt to
`.claude/quality-gates/receipts/<HEAD>.json`. The authoritative field list and write steps
(`mkdir -p`, `git rev-parse HEAD`, the `PASS`/`DEGRADED` verdicts) live in
`gates/primitives/independent-judge.md` › **Handling the verdict** — kept in one place so the
receipt shape can't drift between this overview and the procedure agents actually run.

Properties that matter here: a DEGRADED receipt (an accepted R2 re-read with no subagent) is
allowed, but the hook surfaces it as a visible allow-reason. The receipt is **commit-bound** — a
new commit changes HEAD, so a stale pass cannot authorise a later ship. Receipts live under
`.claude/quality-gates/receipts/` (gitignored); this is what the hook checks before allowing
`gh pr create` / `gh pr merge`.
