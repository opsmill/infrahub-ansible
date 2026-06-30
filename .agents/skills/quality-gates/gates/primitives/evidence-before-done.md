# P1 · Evidence-before-done

**Rule:** never claim "done / passing / green / fixed / complete" without pasting the *actual*
command output that proves it. An assertion is not evidence.

**Procedure:**

1. Run the proving command (test, lint, build, `git status`, CI fetch).
2. Paste the command AND its real output into the conversation.
3. Only then make the claim, citing that output.

If you cannot produce the output, the gate **FAILS** — stop and report why.

Composes `superpowers:verification-before-completion`. Applies at EVERY tier.
