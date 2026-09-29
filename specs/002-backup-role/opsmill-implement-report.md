# Implementation Report: Backup Role (002-backup-role) — INCOMPLETE

- **Feature**: `opsmill.infrahub.backup` role (issue #163)
- **Spec dir**: `specs/002-backup-role`
- **Base commit**: `53af4f9` · **Head commit**: `56499bc` (before this report)
- **Wall clock**: ~35 min (15:36Z → 16:10Z, 2026-09-29)
- **Status**: INCOMPLETE. 29 of 30 tasks are done. T030 (end-to-end on a real Linux systemd host with Infrahub) was not executed: no such host was available. All local tests pass.

## 1. Chunk ledger

| # | Chunk | Tasks | ✅/⚠️/❌ | Commits | Flagged |
|---|---|---|---|---|---|
| 1 | Setup | T001–T002 | 2/0/0 | `31b50d3` | lint leaves an untracked `.ansible/` dir (not committed) |
| 2 | Foundational | T003–T007 | 5/0/0 | `62630d4` | no `no_log` on the credentials-pair assert (it would hide the contract message); arch check uses `in` (2.19 strict conditionals); placeholder `setup_systemd.yml` |
| 3 | US1 tests | T008–T010 | 3/0/0 | `57b36f4` | TDD: the render test failed as expected until chunk 4; `-e` values are not echoed at `-vvv` (checked) |
| 4 | US1 impl | T011–T019 | 9/0/0 | `a3c43cb`, `6915610` | handler renamed `Reload systemd for Infrahub backup` (avoids a global-name clash with the install role); inline `daemon_reload` before the timer starts; unit directory created |
| 5 | US2 S3 | T020–T021 | 2/0/0 | `5498dcf` | "no `--s3-` token" check narrowed so the `%`-escape check on `--s3-prefix` is kept; flag order is asserted |
| 6 | US3 | T022–T025 | 4/0/0 | `08647ce` | **run-now passes credentials on stdin to a `/bin/sh` wrapper**, because `environment:` leaked them at `-vvv`/`ps` even with `no_log`; failure is surfaced by a separate fail task; separate `test_run_now.yml` |
| 7 | Polish | T026–T030 | 4/1/0 | `d498107`, `5c3b3fb`, `2d408b2`, `6c78ebc` | restore URL is `…/backup/backup/restore` (the planned URL returns 404); readme template fixed to one role per line; CHANGELOG uses `Unreleased` (top entry v1.9.0 vs galaxy 1.8.3); T030 ⚠️ not executed |
| R | Review fixes | — | — | `ef49e60`, `56499bc` | see §5 |

## 2. Tasks not completed

- **T030**: end-to-end quickstart on a Linux systemd host with Infrahub. Not executed because this machine is macOS with no systemd, so no such host was available. Never exercised for real: tool download and checksum, timer enable/start, the handlers, stop/disable on opt-out, `become_user`, and a real backup against Infrahub. Commands to run are in `quickstart.md`.

## 3. Local-pass evidence

| Test id | Type | Run command | Passed at | Environment | Verbatim pass line |
|---|---|---|---|---|---|
| `tests/roles/backup/test_validation.yml` (10 failure-contract cases) | integration (localhost) | `bash tests/roles/backup/run.sh` | 2026-09-29T16:09:10Z | macOS arm64, ansible-core 2.19.11rc1 via uv, `-c local`, no become | `localhost : ok=44 changed=0 unreachable=0 failed=0 skipped=30 rescued=10 ignored=0` |
| `tests/roles/backup/test_render.yml` run 1 (default, S3, flags, nosystemd plays) | integration | same | 2026-09-29T16:09:10Z | same | `localhost : ok=60 changed=21 unreachable=0 failed=0 skipped=53 rescued=0 ignored=0` |
| `tests/roles/backup/test_render.yml` run 2 (idempotency, SC-002) | integration | same | 2026-09-29T16:09:10Z | same | `localhost : ok=60 changed=0 unreachable=0 failed=0 skipped=47 rescued=0 ignored=0` |
| `tests/roles/backup/test_run_now.yml` (fake tool: success + failure) | integration | same | 2026-09-29T16:09:10Z | same | `localhost : ok=31 changed=12 unreachable=0 failed=0 skipped=25 rescued=1 ignored=0` |
| `tests/roles/backup/run.sh` (secret grep over all `-vvv` logs, changed=0, secret stored) | integration | same | 2026-09-29T16:09:10Z | same | `PASS: backup role tests` |
| quickstart e2e | e2e | see `quickstart.md` | deferred — local E2E not supported | Linux systemd + Docker Compose Infrahub | — |

Other checks:
- **Passed:**
  - `uv run ansible-lint roles/backup` (0 failures, production profile)
  - yamllint on `roles/backup` and `tests/roles/backup`
  - `uv run mypy .`
  - `invoke tests-sanity`, which only passed after `.ansible/` was temporarily moved out
  - `invoke galaxy-build` (tarball contains `roles/backup/`)
- **`invoke lint`:** fails only on the untracked `.ansible/` copy; clean on tracked files.
- **Not run:** `invoke docusaurus` (no pnpm) and Vale (not installed).

## 4. Review findings

| Sev | Source | File | Summary | Status |
|---|---|---|---|---|
| High | errors | `tasks/validate.yml` | Invalid env key made `/bin/sh` print `KEY=secret` to stderr, which the fail message then showed | ✅ fixed: key/value validation, sentinel-tested |
| High | errors | `tasks/main.yml` | run-now ran as root while the timer runs as `service_user` | ✅ fixed: `become_user` |
| Medium→High | code/errors | env file vs wrapper | systemd EnvironmentFile unquotes/unescapes values the wrapper takes literally; newline injection | ✅ fixed: reject `\n \r \ " ' $` and leading/trailing whitespace |
| High | comments/code | `backup.mdx` | Pre-upgrade example said the timer is untouched, but `setup_systemd: false` disables it | ✅ fixed |
| High | comments | `backup.mdx` | S3 pruning also needs `s3:ListBucket` | ✅ fixed |
| High | tests | tests | Architecture row, download URL/checksum shape and several flags were untested | ✅ fixed: tests added |
| Medium | errors | `tasks/main.yml` | Custom URL without a checksum gave a confusing error; architecture checked even when `install_tool` is false | ✅ fixed |
| Medium | comments | `backup.mdx`, handlers, CHANGELOG | Credential-path wording, always-passed flags, retention floor, "prefixed" comment | ✅ fixed |
| Low | code | `service.j2` | `$` not escaped; binary path unescaped | ✅ fixed (`$$`, path quoted/escaped) |
| Low | code | `service.j2` | shlex `'"'"'` mid-word quoting in ExecStart | deferred: needs a `'` in a path or prefix |
| Medium | errors | `tasks/main.yml` | Fail message shows only one of stderr/stdout | deferred |
| Low | errors | `tasks/main.yml` | No warning when the timer exists but `manage_state` is false | deferred |
| Low | errors | `service.j2` | `Requires=docker.service` assumes the stock unit name (snap Docker differs) | deferred |
| Medium | tests | tests | Schedule-change re-apply, "exactly one backup", type-error case, SC-006 drift script, config dir 0700 | deferred |
| Advisory | simplify | role | Build the credential env once; drop the redundant reload handler; owner/`become` helpers; table-driven validation tests | deferred (advisory) |
| — | types | — | Not applicable (no type definitions in an Ansible role) | skipped |

## 5. Autonomous decisions

- **Deferred e2e:** the quickstart e2e was not run locally (flagged). The role has never run against real systemd or Infrahub, so treat this as unverified until someone runs `quickstart.md`.
- **Chunking:** US1 (12 tasks) was split into tests (T008–T010) and implementation (T011–T019).
- **Credential passing on stdin** instead of `environment:` for run-now. This departs from plan R6 and is documented in `research.md` and the docs.
- **Stricter value validation:** passwords containing quotes, `\` or `$` are now rejected rather than silently mangled by systemd. This is a UX restriction to confirm.
- **`Unreleased` changelog heading:** there is a version mismatch (CHANGELOG v1.9.0 vs `galaxy.yml` 1.8.3), and someone needs to pick the release number.
- **Generated readme churn:** the readme's plugin order is nondeterministic, so that part of the regenerated diff was reverted.

## 6. Suggested next steps

1. Run `quickstart.md` end-to-end on a Linux VM with Infrahub (US1–US3 plus the MinIO variant). Then tick T030.
2. Decide the release version for the CHANGELOG entry.
3. Follow-ups that need approval because they touch `.github/workflows`:
   - wire `tests/roles/backup/run.sh` into CI
   - add `infrahub-backup` to the dependency-bump automation
   - consider ignoring `.ansible/` in `.gitignore`
4. Optionally address the deferred review items and the simplify suggestions.
5. Open a PR against `develop` (not done by this run).
