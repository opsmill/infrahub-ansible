# P2 · Independent judge (author≠judge)

Run at every **ship gate** (see `gate-model.md`). The thing that wrote the artifact cannot be the
thing that certifies it.

## Dispatch contract

Dispatch a **fresh subagent** (Claude Code: the Agent/Task tool, general-purpose). Pass it EXACTLY
these three things and NOTHING else:

1. **The original criteria, verbatim, by reference (R1)** — fetch it fresh: the GitHub issue
   body, the `.bug-analysis-<key>.md`, the spec/PRD — or, for a CI-fix gate, the pre-fix failing
   CI log. Do NOT pass your own summary or your "what I did" narrative.
2. **The artifact under review** — the diff (`git diff <base>...HEAD`) or the specific file(s).
3. **An adversarial instruction** — "Find why this does NOT satisfy the criteria. Apply the
   forbidden-evasions list in `anti-gaming.md` for this gate kind. Return PASS or FAIL with
   specific reasons."

The judge returns **PASS/FAIL + reasons**.

### Per-criterion rubric and determinism

Before issuing the aggregate verdict, the judge evaluates each pass criterion as a **separate Y/N
item**. For a fix gate, for example:

- (a) Does the change address the documented root cause?
- (b) Is the fix general, not test-specific?
- (c) Is the test the test-writer wrote unmodified?
- (d) Is scope respected (no changes outside the fix strategy)?

The judge **reasons through the evidence for each item before stating any verdict**, then combines
them into the aggregate PASS/FAIL. The judge runs at **temperature 0 / lowest-variance setting**
and uses a judge model at least as capable as the implementer.

### N=3 majority for T2 ship gates

For **T2 ship gates**, dispatch the judge **3 times independently** and take the **majority
verdict**: 2 or more FAILs → FAIL; a single dissenting FAIL does not block. A single dissenting
PASS does not unblock.

Verify gates use a **single judgment** (see the verify-gate procedure in `gate-model.md`).

### Portability note

Claude Code's Agent/Task tool gives a context-isolated judge. Codex CLI has **no equivalent
isolation primitive**: under Codex the judge degrades to a fresh-context re-read in the same
agent (R2 mode) and **MUST declare itself degraded** — mechanical independence holds only under
Claude Code.

## Handling the verdict

- **FAIL:** STOP. Do NOT perform the irreversible action. Surface the reasons, fix, and re-run
  the gate from the top.
- **PASS (Claude Code hook enforcement; no-op on engines without the hook):** before the
  irreversible action, run `mkdir -p .claude/quality-gates/receipts` and write
  `.claude/quality-gates/receipts/<HEAD>.json` (HEAD = `git rev-parse HEAD`) containing:

  ```json
  {
    "gate": "<gate name>",
    "sha": "<HEAD commit sha>",
    "verdict": "PASS",
    "criteria_ref": "<issue / .bug-analysis / spec or CI-log ref>",
    "judged_at": "<ISO-8601 timestamp>",
    "judge": "<agent or model>"
  }
  ```

  For an accepted R2 DEGRADED re-read, write the same with `"verdict": "DEGRADED"`. Then proceed
  with the irreversible action.

## Degrade rule (R2)

If a fresh subagent cannot be dispatched (e.g. you are already a deeply-nested subagent, or you
are running under Codex), fall back to the **verify-gate procedure** (lighter re-read) AND tell
the developer: "judge ran in degraded mode — no subagent available." Never silently skip the gate.

Composes `superpowers:requesting-code-review`.

## Human-as-judge rule (R4)

R4 (human-as-judge): when the workflow already has a mandatory human-approval step before the
irreversible action, that approval IS the independent judgment — no subagent is dispatched.
Skills in this category (`creating-issues`, `grilling-ideas`) get P1 only (show the draft as
evidence) plus the human gate already present; bolting a subagent onto a step a human already
signs off adds cost without adding an independent perspective.
