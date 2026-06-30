# DECISION.md — quality-gates ADRs

## ADR-001: In-workflow quality gates over louder prompts

**Context:** Every skill `MUST`/`STOP` is a prompt the agent may ignore; the repo has no hook/CI
enforcement. **Decision:** the critical steps become gates (independent verification + evidence +
STOP-on-fail). **Alternatives:** louder markdown (still a prompt); programmatic hooks (Claude-only,
won't port to Codex). **Consequences:** more deliberate friction at critical steps (Pattern 7).

## ADR-002: Author≠judge via a fresh subagent (P2)

**Context:** a passing self-check proves the author agrees with itself. **Decision:** ship gates
dispatch a fresh subagent given the ORIGINAL criteria (R1), never the author's summary.
**Consequences:** self-certification is impossible at ship gates; ~2x work at those points.

## ADR-003: Hybrid judge by gate purpose

**Decision:** full subagent on irreversible ship gates; lighter fresh-context re-read on
intermediate verify gates. **Consequences:** rigor concentrated where reversal is impossible.

## ADR-004: opsmill-dev is the canonical copy (R3)

**Context:** plugins ship independently, so the reference is duplicated. **Decision:**
`opsmill-dev/skills/quality-gates/` is canonical; `opsmill-repo`'s is a synced copy;
divergence resolves to software. **Consequences:** maintenance must update both; a cross-plugin
drift check is deferred (YAGNI).
