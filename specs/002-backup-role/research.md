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
- **Secrecy in Ansible output**: the env-file `template` task sets `no_log: true` **and** `diff: false` (otherwise `--diff` prints the file). The on-demand `command` task passes credentials via `environment:` and sets `no_log` when credentials are set. Argument spec marks both options `no_log: true`.
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
