# Implementation Report: Backup Role (002-backup-role)

## Iteration 2 (2026-09-30) — INCOMPLETE

- **Source**: [grill-decisions.md](grill-decisions.md) (17 user decisions from the grilling session)
- **Spec dir**: `specs/002-backup-role`
- **Branch**: `backup-role`. It was `issue-163` at the start and was renamed outside this session; the commits are unchanged.
- **Base commit**: `b74a190` · **Head commit**: `af4168b` (before this report)
- **Wall clock**: ~40 min (13:30Z → 14:10Z)
- **Status**: INCOMPLETE. All 12 Iteration 2 tasks (T031–T042) are done, and all local tests pass. T030 (the manual end-to-end test on a real host) is still open.

### 1. Chunk ledger

| # | Chunk | Tasks | ✅/⚠️/❌ | Commits | Flagged |
|---|---|---|---|---|---|
| 1 | Phase 7: interface, defaults, encryption, platform split | T031–T034 | 4/0/0 | `7e7bb64`, `0c19398` | `retention_count: 7` is set only in `defaults/main.yml`, because an argument-spec `default:` makes `null` fail as "cannot convert to int". Added a check that `encrypt_key` is an absolute path. `7e7bb64` fails on its own (it uses the platform variable defined in the next commit), so squash if every commit must pass |
| 2 | Phase 8: exact value round-trip | T035–T039 | 5/0/0 | `b1a4606`, `011d10b` | Env file uses `KEY="…"` with `\ " $ \`` escaped, and run-now sources it via `sh`. **The systemd side is verified**: systemd 252 in a privileged Debian 12 container returned the same hashes as sh (dash and macOS sh). The CR test value is `…\rx`, because Jinja drops a trailing CR |
| 3 | Phase 9: docs and CI | T040–T042 | 3/0/0 | `28e194c`, `b487c2b`, `d9f756d` | New `backup-role-tests` CI job, added to `all_green`. Docs table matches the argument spec for all 35 options. `build_ignore` in `galaxy.yml` misses `.venv`, `specs/` and others; this predates this branch |
| R | Review fixes | — | — | `344e567`, `8250eb5`, `af4168b` | See §4 |

### 2. Tasks not completed

- **T030**: end-to-end test on a real host. The pieces:
  - **Systemd behaviour** (timer, handlers, disabling the timer): not tested. It could now be checked locally, because a systemd container works on this machine.
  - **A real backup against Infrahub** under Docker Compose: needs a real host.

### 3. Local-pass evidence

| Test id | Type | Run command | Passed at | Environment | Verbatim pass line |
|---|---|---|---|---|---|
| `test_validation.yml` (15 failure cases) | integration | `bash tests/roles/backup/run.sh` | 2026-09-30T14:04:34Z | macOS arm64, ansible-core 2.19.11rc1, uv | `localhost : ok=78 changed=0 unreachable=0 failed=0 skipped=36 rescued=14 ignored=0` |
| `test_validation.yml` incl. Linux-only service-user check | integration | `ansible-playbook … test_validation.yml` | 2026-09-30T14:0xZ | `python:3.12-slim` container, unprivileged user | `localhost : ok=88 changed=0 unreachable=0 failed=0 skipped=38 rescued=15 ignored=0` |
| `test_render.yml` run 1 | integration | `bash tests/roles/backup/run.sh` | 2026-09-30T14:04:34Z | macOS | `localhost : ok=87 changed=27 unreachable=0 failed=0 skipped=78 rescued=0 ignored=0` |
| `test_render.yml` run 2 (idempotency) | integration | same | 2026-09-30T14:04:34Z | macOS | `localhost : ok=87 changed=0 unreachable=0 failed=0 skipped=70 rescued=0 ignored=0` |
| `test_render_no_secrets.yml` (null credentials) | integration | same | 2026-09-30T14:04:34Z | macOS | `localhost : ok=14 changed=3 unreachable=0 failed=0 skipped=16 rescued=0 ignored=0` |
| `test_run_now.yml` (hash round-trip + failure) | integration | same | 2026-09-30T14:04:34Z | macOS | `localhost : ok=37 changed=12 unreachable=0 failed=0 skipped=29 rescued=1 ignored=0` |
| `envfile_roundtrip.sh` + `run.sh` aggregate | integration | same | 2026-09-30T14:04:34Z | macOS | `PASS: backup role tests` |
| `envfile_roundtrip.sh` under dash | integration | run in `debian:12` | 2026-09-30T13:41:24Z | Debian 12, `/bin/sh -> dash` | `ok:` for all 3 keys |
| systemd EnvironmentFile round-trip | integration | `systemd-run --wait --pipe --quiet -p EnvironmentFile=/tmp/test.env sh -c 'printf %s "$KEY" \| sha256sum'` | 2026-09-30T13:42:37Z | privileged Debian 12 + systemd 252 container (built locally) | `MATCH AWS_ACCESS_KEY_ID` / `MATCH AWS_SECRET_ACCESS_KEY` / `MATCH INFRAHUB_DB_PASSWORD` |
| quickstart e2e | e2e | `quickstart.md` | deferred — local E2E not supported | Linux host + Infrahub on Docker Compose | — |

Other checks:

- **Passed:**
  - ansible-lint (production profile)
  - yamllint
  - mypy
  - `invoke tests-sanity`, with `.ansible/` moved aside for the run
  - `invoke galaxy-build`
  - actionlint on the CI job
  - rumdl on all files this branch added
- **Still failing, predates this branch:** rumdl on `plugins/AGENTS.md`. CI's `markdown-lint` job runs `rumdl check .`, so it fails until that file is fixed.

### 4. Review findings

| Sev | File | Summary | Status |
|---|---|---|---|
| High | `vars/main.yml` | `retention_days: null` rendered `--retention-days None`, so every scheduled run would fail with no warning | ✅ fixed and tested |
| Medium | `tasks/docker/validate.yml` | A missing `service_user` failed only after the binary was installed | ✅ fixed: `getent` check; the test runs on Linux only |
| Medium | docs | Run-now as an unprivileged `service_user` needs pipelining or ACLs | ✅ documented |
| Medium | tests | Nothing checked `service_user` / `User=`, the absence of `OnFailure`, or that the secret stays out of the argument list | ✅ tests added |
| Medium | tests/CI | The systemd side of the round-trip is checked by hand only, not in CI | deferred |
| Low | `tasks/validate.yml` | `config_directory` must be absolute | ✅ fixed |
| Low | vars/template | A `null` credential rendered `"None"` | ✅ fixed and tested |
| Low | docs | `AWS_*` keys in `backup_infrahub_environment` override the S3 variables | ✅ documented |
| Low | docs/specs | Key path mismatch, the facts claim, edition and retention wording, stale R4/R12 | ✅ fixed |
| Low | `run.sh` | Locale-dependent `sort` | ✅ `LC_ALL=C` |
| Low | tests | Run-now as a non-root `become_user` has no integration test | deferred |
| — | — | `rumdl` failures in this branch's spec files and `CLAUDE.md` | ✅ fixed (`344e567`) |

### 5. Autonomous decisions

- **Implementation order:** followed the Phase 7–9 layout in `tasks.md`, one chunk each.
- **Where the 7 lives:** only in `defaults/main.yml`, so that `null` still turns retention off. The docs table special-cases it.
- **Test isolation:** the service-user check only runs on Linux. Null credentials are tested in a separate playbook, because `-e` extra vars would override them.
- **Deferred:** a systemd round-trip job in CI, and an integration test for an unprivileged `become_user`.
- **Deferred e2e:** the quickstart end-to-end was not run locally. Please confirm that's acceptable.

### 6. Suggested next steps

1. Run T030: systemd timer and handler behaviour in a systemd container (possible locally now), plus a real backup against Infrahub on a Linux VM.
2. Fix `plugins/AGENTS.md` rumdl issues (predate this branch), or CI's `markdown-lint` job will fail.
3. Ask the infrahub-backup maintainers whether `--encrypt`/`--encrypt-key` are ready for customers; they're absent from the published docs.
4. Squash `7e7bb64` + `0c19398` if every commit must pass on its own; then open a PR against `develop`.

---

## Iteration 1 report (2026-09-29) — INCOMPLETE

- **Feature**: `opsmill.infrahub.backup` role (issue #163)
- **Spec dir**: `specs/002-backup-role`
- **Base commit**: `53af4f9` · **Head commit**: `56499bc` (before this report)
- **Wall clock**: ~35 min (15:36Z → 16:10Z, 2026-09-29)
- **Status**: INCOMPLETE. 29 of 30 tasks are done. T030 (end-to-end on a real Linux systemd host with Infrahub) was not executed: no such host was available. All local tests pass.

### 1. Chunk ledger

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

### 2. Tasks not completed

- **T030**: end-to-end quickstart on a Linux systemd host with Infrahub. Not executed because this machine is macOS with no systemd, so no such host was available. Never exercised for real: tool download and checksum, timer enable/start, the handlers, stop/disable on opt-out, `become_user`, and a real backup against Infrahub. Commands to run are in `quickstart.md`.

### 3. Local-pass evidence

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

### 4. Review findings

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

### 5. Autonomous decisions

- **Deferred e2e:** the quickstart e2e was not run locally (flagged). The role has never run against real systemd or Infrahub, so treat this as unverified until someone runs `quickstart.md`.
- **Chunking:** US1 (12 tasks) was split into tests (T008–T010) and implementation (T011–T019).
- **Credential passing on stdin** instead of `environment:` for run-now. This departs from plan R6 and is documented in `research.md` and the docs.
- **Stricter value validation:** passwords containing quotes, `\` or `$` are now rejected rather than silently mangled by systemd. This is a UX restriction to confirm.
- **`Unreleased` changelog heading:** there is a version mismatch (CHANGELOG v1.9.0 vs `galaxy.yml` 1.8.3), and someone needs to pick the release number.
- **Generated readme churn:** the readme's plugin order is nondeterministic, so that part of the regenerated diff was reverted.

### 6. Suggested next steps

1. Run `quickstart.md` end-to-end on a Linux VM with Infrahub (US1–US3 plus the MinIO variant). Then tick T030.
2. Decide the release version for the CHANGELOG entry.
3. Follow-ups that need approval because they touch `.github/workflows`:
   - wire `tests/roles/backup/run.sh` into CI
   - add `infrahub-backup` to the dependency-bump automation
   - consider ignoring `.ansible/` in `.gitignore`
4. Optionally address the deferred review items and the simplify suggestions.
5. Open a PR against `develop` (not done by this run).
