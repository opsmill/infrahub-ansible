# Research: Backup Role (002-backup-role)

Sources: `infrahub-backup` docs (`docs/docs/backup/{create,install,retention}.mdx`, `docs/docs/reference/{commands,configuration}.mdx` in opsmill/infrahub-backup, fetched 2026-09-29), release `v2.3.0` assets, and the existing `roles/install` role.

## R1 — Wrap the official tool, do not reimplement

- **Decision**: The role installs and drives `infrahub-backup` (OpsMill's Backup & Restore CLI).
- **Rationale**: The tool owns the hard parts — quiescing the app, Neo4j + Prefect PostgreSQL dumps, archive format, checksums, S3 upload, retention pruning. Reimplementing any of it in Ansible would drift from the supported restore path.
- **Alternatives**: raw `docker compose exec` + `neo4j-admin dump` tasks (rejected: unsupported archive format, no restore compatibility); shelling to the tool from a cron entry (rejected: issue explicitly asks for systemd).

## R2 — Tool distribution and checksum verification

- **Decision**: Download from `https://github.com/opsmill/infrahub-backup/releases/download/<version>/infrahub-backup-linux-<arch>` with `ansible.builtin.get_url`, `checksum: "sha256:<release>/SHA256SUMS"`, `dest: /usr/local/bin/infrahub-backup`, `mode: "0755"`. Default version pinned to `v2.3.0`.
- **Rationale**: Release publishes `infrahub-backup-linux-amd64`/`-arm64` and a `SHA256SUMS` file (verified: `45e15ed1…  infrahub-backup-linux-amd64`). `get_url` with a checksum URL looks up the line matching the source URL basename, so the default URL works unchanged. With `dest` a file and a checksum, `get_url` skips the download when the existing file matches → idempotent; a version bump changes the checksum → re-download (upgrade path).
- **Arch map**: `x86_64`→`amd64`; `aarch64`/`arm64`→`arm64`; anything else → fail with explicit message (spec edge case).
- **Air-gap**: `backup_infrahub_tool_url` and `backup_infrahub_tool_checksum` overrides. When the URL is overridden and its basename differs, the operator sets the checksum explicitly (documented).
- **Alternatives**: `https://infrahub.opsmill.io/ops/<OS>/<arch>/infrahub-backup` (rejected: always "latest", unpinned, no checksum); tool's `update` self-updater (rejected: interactive, non-idempotent).

## R3 — How configuration reaches the tool

- **Decision**: Non-secret options are passed as **CLI flags** built once in `vars/main.yml` (`backup_infrahub_create_args`) and reused by both the systemd unit `ExecStart` and the on-demand task. **Secrets only** (AWS key pair) go into an `EnvironmentFile` at `/etc/infrahub-backup/infrahub-backup.env`, mode `0600`, owner root.
- **Rationale**: Flags are the tool's highest-precedence, best-documented channel. The docs are inconsistent on env var names (`install.mdx` shows `INFRAHUB_COMPOSE_PROJECT`/`BACKUP_DIR`; the reference shows `INFRAHUB_PROJECT`/`INFRAHUB_BACKUP_DIR`), and boolean env parsing is undocumented — flags avoid both risks. AWS credentials use the standard `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` chain the tool documents; keeping them out of the unit file keeps them out of `systemctl cat` and world-readable `/etc/systemd/system`.
- **Secrecy in Ansible output**: the env-file `template` task sets `no_log: true` **and** `diff: false` (otherwise `--diff` prints the file). The on-demand `command` task passes credentials as `KEY=value` lines on the module's `stdin`, exported by a `/bin/sh` wrapper, and sets `no_log` when credentials are set. (Implementation finding: `environment:` puts values on the remote command line, visible in `ps` and printed in the `-vvv` `EXEC` line even under `no_log`.) Because `no_log` would also hide the tool's error, the result is registered with `failed_when: false` and a follow-up `fail` task surfaces the tool's stderr (US3-AS2). Argument spec marks both options `no_log: true`.
- **Alternatives**: everything in env file (rejected: env-name ambiguity above); credentials in unit `Environment=` (rejected: unit files are 0644).

## R4 — systemd layout

- **Decision**: `infrahub-backup.service` (`Type=oneshot`, optional `OnFailure=<backup_infrahub_on_failure>` in `[Unit]` (critique E1), `After=docker.service`, `Requires=docker.service`, `EnvironmentFile=-<env file>`, `ExecStart=<bin> <args>`, `User=` configurable default `root`) + `infrahub-backup.timer` (`OnCalendar=<schedule>` default `*-*-* 02:00:00`, `Persistent=true`, `RandomizedDelaySec=` configurable default `0`, `WantedBy=timers.target`). Timer enabled + started; service never enabled (triggered by timer).
- **Rationale**: Mirrors the tool's documented unit pair; `Persistent=true` satisfies "missed run executes at boot". Units rendered via `template` notify handlers `Reload systemd` → `Restart Infrahub backup timer`, mirroring the install role's handler style. `WantedBy=timers.target` (not `cloud-init.target` like install) because the timer must run on any host.
- **Disable path** (FR-011): when `backup_infrahub_setup_systemd: false`, `stat` the timer unit; if present, stop + disable it. Unit files are left in place (harmless, disabled) — removing them adds no value and complicates idempotency.

## R5 — Input validation

- **Decision**: `meta/argument_specs.yml` for types/choices (Ansible validates automatically at role start). A first `ansible.builtin.assert` task covers what argument specs cannot express: retention values ≥ 1 when set; `s3_bucket` non-empty when `s3_upload` true; both-or-neither S3 credentials; supported architecture.
- **Rationale**: Both run before any host change (SC-005).

## R6 — On-demand backup

- **Decision**: `backup_infrahub_run_now: false` (opt-in). When true, a final `ansible.builtin.command` runs `<bin> <args>` with `changed_when: true`. Runs after handlers are flushed (`meta: flush_handlers`) so a newly installed tool/config is in place. Command module is skipped in check mode automatically.
- **Rationale**: Deterministic, surfaces the tool's stderr on failure (US3-AS2), works with systemd disabled (US3-AS3). Running via `systemctl start` would hide the error in the journal.

## R7 — Privilege model

- **Decision**: Tasks use `become: "{{ backup_infrahub_become }}"`, default `true`.
- **Rationale**: Matches install role behaviour (it hardcodes `become: true`) while letting the validation tests run unprivileged on a dev machine. Small, justified deviation.

## R8 — Excluded tool features

- `--redact` (destroys the live DB) — never exposed (FR-015).
- `restore`, `prune` standalone — out of scope; retention is applied through `create --retention-*`.
- `--sleep` — only useful for manual transfer; not exposed.
- Kubernetes — Helm chart subchart exists; out of scope.

## R9 — Testing approach

- **Decision**: Three tiers, none requiring a live Infrahub:
  1. `ansible-lint` (production profile, already in CI; covers `roles/`) and `ansible-playbook --syntax-check`.
  2. **Validation playbook** `tests/roles/backup/test_validation.yml` run on `localhost` with `backup_infrahub_become: false`: each invalid input in a `block`/`rescue`, asserting the role failed with the expected message and that no file was written under a temp prefix.
  3. **Render playbook** `tests/roles/backup/test_render.yml`: run the role against temp dirs with the tool install and systemd *activation* skipped via internal switches (`backup_infrahub_install_tool: false`, units rendered to a temp `backup_infrahub_systemd_directory` with `backup_infrahub_manage_systemd_state: false`), then assert on rendered unit/env content and file modes, run it twice and assert zero changes on the second pass (SC-002), and check file modes/content. **Secrecy** (SC-004) is checked by `tests/roles/backup/run.sh`, which runs `test_render.yml` with `-vvv --diff`, tees the output to a temp file, and fails if the sentinel secret string (`SENTINEL-SECRET-e3b0c442`) appears — a play cannot observe its own stdout (critique E3).
  - Plus a **manual end-to-end** check on a Linux systemd host running Infrahub (quickstart.md), recorded in the implementation report if not executed.
- **Rationale**: The repo has no role tests today; unit/sanity tiers target Python plugins. Tiers 2–3 run in seconds with only `ansible-core`.
- **Alternatives**: Molecule (rejected: new dependency, needs Docker-with-systemd); nothing (rejected: SC-002/004/005 would be unverified).

## R10 — Documentation and changelog

- `docs/docs/references/roles/backup.mdx` is hand-written (like `install.mdx`; only `references/plugins/*.mdx` and `readme.mdx` are generated). `invoke generate-doc` regenerates `readme.mdx`, which lists roles from `roles/*/meta/main.yml`.
- `CHANGELOG.rst` is edited in feature PRs (see `bc0ee34`): add a "New Roles" entry.

---

# Iteration 2 research (2026-09-30, from grill-decisions.md)

## R11 — One quoting scheme shared by systemd and the run-now wrapper (decision 11)

- **Decision**: Render every env-file entry as `KEY="<value>"` with exactly four characters backslash-escaped: `\`, `"`, `$`, `` ` ``. Run-now stops feeding secrets on stdin; it runs `/bin/sh -c 'set -a; . "$1"; set +a; shift; exec "$@"' sh <env_file> <bin> <args…>`, i.e. it **sources the same file**.
- **Rationale**: systemd's `EnvironmentFile=` parser (`load_env_file`, no variable expansion) and POSIX `sh` double-quoted strings recognise the same backslash escapes (`\\`, `\"`, `\$`, `` \` ``) and keep whitespace inside quotes. One file, one rendering, identical value in both paths. Removes the stdin wrapper and the character blacklist. Newlines/CR stay rejected (no credential contains them; a `\`+newline is a line continuation in both parsers).
- **Must verify empirically** (task): sh side locally with adversarial values (`a"b`, `a\b`, `$HOME`, `` `id` ``, `'`, leading/trailing spaces, `\\$`); systemd side in a systemd-enabled Linux container if Docker is available (`systemd-run --wait --pipe -p EnvironmentFile=… printenv KEY`), else record as e2e item.
- **Verified (T035/T039, 2026-09-30)**: values ` SENTINEL-SECRET-e3b0c442 a"b\c$HOME`x'y ` (leading/trailing space), `  $(id) \\$ "q" 'z' SENTINEL-SECRET-e3b0c442` and `AKIATEST`, rendered by the role, give identical sha256 in all four readers: macOS `/bin/sh` (bash 3.2 sh mode) and Debian 12 dash via `set -a; . file` (`tests/roles/backup/envfile_roundtrip.sh`); the run-now wrapper (fake tool hashes, `run.sh`); systemd 252 (Debian 12, privileged container) via `systemd-run --wait --pipe -p EnvironmentFile=/tmp/test.env sh -c 'printf %s "$KEY" | sha256sum'` and via a `Type=oneshot` unit with `EnvironmentFile=`. No character needed narrowing; only newline/CR stays rejected. Note: `systemd-run` needs D-Bus in the container; `jrei/systemd-debian:12` has no arm64 image, so a local `debian:12` + `systemd systemd-sysv dbus` image was used.
- **Consequence**: the env file must be readable by the run-now user → config dir and env file owned by `service_user` (mode stays 0700/0600; systemd reads `EnvironmentFile=` as PID 1 regardless).
- **Alternatives**: keep stdin + blacklist (rejected by user); single-quote rendering (cannot represent `'`).

## R12 — Platform dispatch (decision 2)

- **Decision**: `tasks/main.yml` = shared `validate.yml` → `ansible.builtin.include_tasks: "{{ backup_infrahub_platform }}/main.yml"`. Docker files move to `tasks/docker/{main.yml,validate.yml,setup_systemd.yml}`. Shared: flag builder `backup_infrahub_create_args`, retention/S3/encryption/force/metadata validation. Docker-only: arch/tool install, directories, env file, systemd, run-now, env-value checks. Templates stay under `templates/` (they are Docker-only; a later platform adds its own).
- `include_tasks` (dynamic) so a future platform file is only parsed when selected; handlers stay in `handlers/main.yml`, gated by `when` on platform.

## R13 — Tool-default alignment (decision 7)

- `docker_project`, `log_format`, `neo4j_metadata`: no default in `defaults/main.yml` (commented), no default in argument spec; flag emitted only when defined and non-empty. `retention_count: 7` in defaults; `null` → omitted (argument spec `type: int` accepts `None` for a non-required option — verify; if the validator coerces or rejects `None`, document `backup_infrahub_retention_count: ~` behaviour found).

## R14 — Encryption (decision 9)

- Flags verified at tool tag `v2.3.0` (`src/cmd/infrahub-backup/main.go`): `--encrypt` (built-in OpsMill key unless `--encrypt-key`), `--encrypt-key <public key path>` (implies `--encrypt`). Both are `create` flags → after `create` in the token list. Emit `--encrypt-key PATH` when `encrypt_key` set, else `--encrypt` when `encrypt` true. Validate: `encrypt_key`, when set, is an absolute path (no host stat — the operator may place it later in the same play; document).
- Encrypted archives are named `….tar.gz.enc`; tool retention and `restore --latest` already handle them (tool docs).

## R15 — CI job (decision 17)

- Add a job to `.github/workflows/workflow-ansible-linter-and-tests.yml` (reusable workflow called on PRs to `develop`/`stable`): checkout, `astral-sh/setup-uv` (match the version/pinning style already used in the repo's workflows), `uv sync`, `bash tests/roles/backup/run.sh`. Add it to the workflow's aggregate/required job list if one exists (the file has an aggregate job referencing `ansible-lint` and `unit-tests`).
