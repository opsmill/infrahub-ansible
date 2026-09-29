# Tasks: Backup Role for Infrahub Instances

**Input**: `specs/002-backup-role/` — plan.md, spec.md, research.md, data-model.md, contracts/role-interface.md, quickstart.md, critiques/critique-20260929.md

**Tests**: Requested by the plan (research R9, critique E3): localhost test playbooks under `tests/roles/backup/` driven by `run.sh`.

**Authoritative interface**: `contracts/role-interface.md`. Every variable, default, file mode and failure message below comes from it — keep `defaults/main.yml`, `meta/argument_specs.yml` and `docs/docs/references/roles/backup.mdx` identical to it.

**Conventions**: mirror `roles/install/` (YAML style, `---` header, FQCN modules, task names capitalised, handler names in title case). All host-changing tasks use `become: "{{ backup_infrahub_become }}"`. Run `uv run ansible-lint roles/backup tests/roles/backup` after each phase (note `.ansible-lint` excludes `tests/`; lint the role, and `--syntax-check` the tests).

## Phase 1: Setup

- [X] T001 Create role skeleton directories `roles/backup/{defaults,vars,meta,handlers,tasks,templates}` and `tests/roles/backup/`
- [X] T002 [P] Create `roles/backup/meta/main.yml` with `galaxy_info` copied from `roles/install/meta/main.yml`, `description: Back up Infrahub`, `galaxy_tags: [infrahub, backup]`

## Phase 2: Foundational (blocks all stories)

- [ ] T003 Create `roles/backup/defaults/main.yml` with every variable from the contract table that has a default (`backup_infrahub_version: v2.3.0`, `backup_infrahub_install_tool: true`, `backup_infrahub_bin_path: /usr/local/bin/infrahub-backup`, `backup_infrahub_backup_directory: /var/backups/infrahub`, `backup_infrahub_backup_directory_mode: "0700"`, `backup_infrahub_config_directory: /etc/infrahub-backup`, `backup_infrahub_docker_project: infrahub`, `backup_infrahub_force: false`, `backup_infrahub_neo4j_metadata: all`, `backup_infrahub_exclude_taskmanager: false`, `backup_infrahub_log_format: text`, `backup_infrahub_s3_upload: false`, `backup_infrahub_s3_keep_local: false`, `backup_infrahub_environment: {}`, `backup_infrahub_setup_systemd: true`, `backup_infrahub_systemd_directory: /etc/systemd/system`, `backup_infrahub_systemd_manage_state: true`, `backup_infrahub_schedule: "*-*-* 02:00:00"`, `backup_infrahub_randomized_delay: "0"`, `backup_infrahub_service_user: root`, `backup_infrahub_run_now: false`, `backup_infrahub_become: true`); list unset ones (`retention_*`, `s3_bucket/prefix/endpoint/region`, credentials, `on_failure`) as commented lines like install does for `install_infrahub_version`
- [ ] T004 Create `roles/backup/meta/argument_specs.yml` (`argument_specs.main`, `short_description: Back up Infrahub`, description lines stating Docker Compose + systemd + Linux x86_64/aarch64 requirements) with one option per contract row: correct `type`, `default` where defined, `choices` for `neo4j_metadata` (`all, none, users, roles`) and `log_format` (`text, json`), `type: int` for retention, `type: dict` for `environment`, `no_log: true` on `s3_access_key_id`, `s3_secret_access_key`, `environment`
- [ ] T005 Create `roles/backup/vars/main.yml`: `backup_infrahub_arch_map` (`x86_64: amd64`, `aarch64: arm64`, `arm64: arm64`); `backup_infrahub_arch: "{{ backup_infrahub_arch_map.get(ansible_facts.architecture) }}"`; `backup_infrahub_release_url: https://github.com/opsmill/infrahub-backup/releases/download/{{ backup_infrahub_version }}`; `backup_infrahub_default_tool_url` / `backup_infrahub_default_tool_checksum` (`sha256:<release_url>/SHA256SUMS`); `backup_infrahub_env_file: "{{ backup_infrahub_config_directory }}/infrahub-backup.env"`; and `backup_infrahub_create_args` — a list built with Jinja: global flags first (`--backup-dir <dir>`, `--project <p>` only when project non-empty, `--log-format <f>`, `--s3-bucket/--s3-prefix/--s3-endpoint/--s3-region` each only when defined and non-empty), then `create`, `--neo4jmetadata <m>`, then `--force`, `--exclude-taskmanager`, `--s3-upload`, `--s3-keep-local` when true, `--retention-days N` / `--retention-count N` when defined. Tool URL/checksum overrides: tasks use `backup_infrahub_tool_url | default(backup_infrahub_default_tool_url)` (so operators set the public name). Also `backup_infrahub_has_secrets: "{{ backup_infrahub_s3_access_key_id is defined or (backup_infrahub_environment | length > 0) }}"`
- [ ] T006 Create `roles/backup/tasks/validate.yml`: one `ansible.builtin.assert` per failure-contract row (retention_days ≥ 1 when defined → `fail_msg` containing `backup_infrahub_retention_days must be >= 1`; same for count; `s3_upload` ⇒ `s3_bucket` defined and non-empty → `backup_infrahub_s3_bucket is required when backup_infrahub_s3_upload is true`; credentials both-or-neither → `backup_infrahub_s3_access_key_id and backup_infrahub_s3_secret_access_key must be set together`; `backup_infrahub_arch` truthy → `Unsupported architecture: <arch>`), each with `quiet: true`; the credentials assert sets `no_log: true`. Preceded by a `ansible.builtin.setup` with `gather_subset: [min]` when `ansible_facts.architecture is not defined` (critique E6)
- [ ] T007 Create `roles/backup/tasks/main.yml` ordering: `import_tasks: validate.yml` → install tool block → directories/env file → `import_tasks: setup_systemd.yml` when `setup_systemd` → disable path when not → `meta: flush_handlers` → run-now (story phases fill in each section)

**Checkpoint**: `ANSIBLE_ROLES_PATH=roles uv run ansible-playbook -i localhost, -c local --syntax-check` on a one-line play including the role passes.

## Phase 3: User Story 1 — Scheduled local backups (P1) 🎯 MVP

**Goal**: default-variable apply → tool installed, backup dir, timer active daily 02:00; idempotent; retention.
**Independent test**: `tests/roles/backup/run.sh` validation + render passes; manual e2e in quickstart.md.

### Tests (write first, expect failure)

- [ ] T008 [P] [US1] Create `tests/roles/backup/test_validation.yml`: `hosts: localhost`, `connection: local`, `gather_facts: false`; a `vars` block pointing every path variable under `/tmp/infrahub-backup-test-validation` (`backup_directory`, `config_directory`, `systemd_directory`, `bin_path`) with `backup_infrahub_become: false`, `backup_infrahub_install_tool: false`, `backup_infrahub_systemd_manage_state: false`; one `block`/`rescue` per failure-contract row using `ansible.builtin.include_role: name: backup` with the offending vars (retention_days 0, retention_count -1, neo4j_metadata `bogus`, s3_upload without bucket, only access key id set), rescue asserts `ansible_failed_result.msg` contains the contract message (argument-spec case: contains `neo4j_metadata`), and a trailing `ansible.builtin.fail` in each block ensures the role did not succeed; finally assert `/tmp/infrahub-backup-test-validation` does not exist (no host change, SC-005)
- [ ] T009 [P] [US1] Create `tests/roles/backup/test_render.yml`: localhost play applying the role with paths under a temp dir passed as `-e test_root=<dir>`, `become: false`, `install_tool: false`, `systemd_manage_state: false`, `setup_systemd: true`, `retention_count: 14`, `s3_prefix: "infra%hub"`, `on_failure: notify@%n.service`; post-tasks assert: service file contains `ExecStart=` with `--retention-count 14`, `--project infrahub`, `infra%%hub`, `create`, and `OnFailure=notify@%n.service` (on_failure is rendered verbatim, not escaped — it is a systemd unit expression); timer contains `OnCalendar=*-*-* 02:00:00` and `Persistent=true`; env file mode `0600`; backup dir mode `0700`
- [ ] T010 [US1] Create `tests/roles/backup/run.sh` (bash, `set -euo pipefail`, executable): creates a temp dir via `mktemp -d`, trap-removes it; runs `test_validation.yml`; runs `test_render.yml` twice with `-vvv --diff -e test_root=$TMP -e backup_infrahub_s3_access_key_id=AKIATEST -e backup_infrahub_s3_secret_access_key=SENTINEL-SECRET-e3b0c442 -e '{"backup_infrahub_environment": {"INFRAHUB_DB_PASSWORD": "SENTINEL-SECRET-e3b0c442"}}'`, tee-ing output to `$TMP/run1.log` / `run2.log`; fails if `grep -q SENTINEL-SECRET-e3b0c442` matches either log; fails unless `run2.log` recap line has `changed=0`; asserts env file contains the secret (it must be *stored*, just not printed). Uses `ANSIBLE_ROLES_PATH=$(repo)/roles` and `uv run ansible-playbook -i localhost, -c local`

### Implementation

- [ ] T011 [US1] In `roles/backup/tasks/main.yml` add the install block (when `backup_infrahub_install_tool`): `ansible.builtin.get_url` `url: "{{ backup_infrahub_tool_url | default(backup_infrahub_default_tool_url) }}"`, `checksum: "{{ backup_infrahub_tool_checksum | default(backup_infrahub_default_tool_checksum) }}"`, `dest: "{{ backup_infrahub_bin_path }}"`, `mode: "0755"`, `owner: root`, `group: root`
- [ ] T012 [US1] In `roles/backup/tasks/main.yml` add `ansible.builtin.file` tasks: backup directory (`state: directory`, `mode: "{{ backup_infrahub_backup_directory_mode }}"`, `owner: "{{ backup_infrahub_service_user }}"` — omit owner when `not backup_infrahub_become` so tests run unprivileged), config directory (`mode: "0700"`)
- [ ] T013 [P] [US1] Create `roles/backup/templates/infrahub-backup.env.j2`: header comment `# Managed by Ansible (opsmill.infrahub.backup) — contains secrets`; `AWS_ACCESS_KEY_ID=` / `AWS_SECRET_ACCESS_KEY=` when set; one `KEY=value` line per `backup_infrahub_environment` item (sorted by key for stable output)
- [ ] T014 [US1] In `roles/backup/tasks/main.yml` add the env file `ansible.builtin.template` (`dest: "{{ backup_infrahub_env_file }}"`, `mode: "0600"`, `no_log: true`, `diff: false`; owner root only when become)
- [ ] T015 [P] [US1] Create `roles/backup/templates/infrahub-backup.service.j2`: `[Unit]` Description, `After=docker.service`, `Requires=docker.service`, `OnFailure=` only when `backup_infrahub_on_failure` defined; `[Service]` `Type=oneshot`, `User={{ backup_infrahub_service_user }}`, `EnvironmentFile=-{{ backup_infrahub_env_file }}`, `ExecStart={{ backup_infrahub_bin_path }} {{ backup_infrahub_create_args | map('quote') | map('replace', '%', '%%') | join(' ') }}`; no `[Install]` section (timer-activated)
- [ ] T016 [P] [US1] Create `roles/backup/templates/infrahub-backup.timer.j2`: `[Unit] Description=Scheduled Infrahub backup`; `[Timer] OnCalendar={{ backup_infrahub_schedule }}`, `Persistent=true`, `RandomizedDelaySec={{ backup_infrahub_randomized_delay }}`, `Unit=infrahub-backup.service`; `[Install] WantedBy=timers.target`
- [ ] T017 [US1] Create `roles/backup/tasks/setup_systemd.yml`: `ansible.builtin.template` for service and timer into `backup_infrahub_systemd_directory` (mode `0644`, owner/group root when become) notifying `Reload systemd` and `Restart Infrahub backup timer`; then `ansible.builtin.systemd_service` `name: infrahub-backup.timer`, `enabled: true`, `state: started` when `backup_infrahub_systemd_manage_state`
- [ ] T018 [US1] Create `roles/backup/handlers/main.yml`: `Reload systemd` (`ansible.builtin.systemd_service: daemon_reload: true`) and `Restart Infrahub backup timer` (`name: infrahub-backup.timer`, `state: restarted`, `enabled: true`), both `when: backup_infrahub_systemd_manage_state | bool`, `become: "{{ backup_infrahub_become }}"`
- [ ] T019 [US1] Run `tests/roles/backup/run.sh` and `uv run ansible-lint roles/backup`; fix until both pass

**Checkpoint**: MVP — scheduled local backups.

## Phase 4: User Story 2 — Remote object storage (P2)

**Goal**: S3 flags + credentials, secrets hidden.
**Independent test**: render assertions for S3 flags; secret grep in `run.sh`.

- [ ] T020 [US2] Extend `tests/roles/backup/test_render.yml` with a second play (`-e test_root` subdir `s3/`) setting `s3_upload: true`, `s3_bucket: infrahub-backups`, `s3_endpoint: http://minio.local:9000`, `s3_region: eu-central-1`, `s3_keep_local: true`; assert ExecStart contains `--s3-bucket infrahub-backups`, `--s3-endpoint http://minio.local:9000`, `--s3-region eu-central-1`, `--s3-upload`, `--s3-keep-local`, and that the service file does not contain `AWS_` (credentials only in env file); assert default play's ExecStart contains no `--s3-` token
- [ ] T021 [US2] Verify `backup_infrahub_create_args` in `roles/backup/vars/main.yml` emits the S3 global flags before `create` and `--s3-upload`/`--s3-keep-local` after it; rerun `tests/roles/backup/run.sh`

## Phase 5: User Story 3 — On-demand backup and systemd opt-out (P3)

**Goal**: `run_now` runs one backup; `setup_systemd: false` installs no units and disables an existing timer.
**Independent test**: render test with `setup_systemd: false` → no unit files; e2e for run_now.

- [ ] T022 [US3] In `roles/backup/tasks/main.yml` add the disable path (when `not backup_infrahub_setup_systemd`): `ansible.builtin.stat` `{{ backup_infrahub_systemd_directory }}/infrahub-backup.timer`; if it exists and `systemd_manage_state`, `ansible.builtin.systemd_service` `name: infrahub-backup.timer`, `state: stopped`, `enabled: false`
- [ ] T023 [US3] In `roles/backup/tasks/main.yml` after `meta: flush_handlers` add run-now: `ansible.builtin.command` `argv: "{{ [backup_infrahub_bin_path] + backup_infrahub_create_args }}"`, `environment:` built from credentials (`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` when set) combined with `backup_infrahub_environment`, `no_log: "{{ backup_infrahub_has_secrets | bool }}"`, `changed_when: true`, `when: backup_infrahub_run_now | bool`
- [ ] T024 [US3] Extend `tests/roles/backup/test_render.yml` with a play (`test_root` subdir `nosystemd/`) using `setup_systemd: false` asserting neither unit file exists and the env file still exists
- [ ] T025 [US3] Run `tests/roles/backup/run.sh` and `uv run ansible-lint roles/backup`

## Phase 6: Polish & Cross-Cutting

- [ ] T026 [P] Create `docs/docs/references/roles/backup.mdx` modelled on `docs/docs/references/roles/install.mdx`: overview; requirements (Linux systemd, x86_64/aarch64, Docker Compose v2, outbound HTTPS to GitHub or overridden URL, facts); role-variables table identical to the contract; examples in `<Tabs>`: quick start (install + backup roles in one play), remote S3/MinIO with vaulted credentials, pre-upgrade on-demand (`run_now: true`, `setup_systemd: false`); sections "Checking scheduled backups" (`systemctl list-timers infrahub-backup.timer`, `journalctl -u infrahub-backup.service`, `backup_infrahub_on_failure`), "Things to know" (Community Edition stops the app during backup → schedule in a maintenance window; `--s3-upload` removes the local archive unless `s3_keep_local`; S3 retention needs delete permission; redact is not exposed), "Restore" (manual, link `https://docs.infrahub.app/backup/restore`), "Air-gapped installs" (override `tool_url` + `tool_checksum`)
- [ ] T027 [P] Add to top of `CHANGELOG.rst` a new unreleased section following the file's existing RST style with a `New Roles` subsection: ``- ``backup`` - Install the infrahub-backup CLI and schedule local or S3 backups of an Infrahub instance with a systemd timer.``
- [ ] T028 Run `invoke generate-doc` and confirm `docs/docs/readme.mdx` lists `backup` under Roles; revert any unrelated generated churn only if it stems from nondeterministic ordering (report it otherwise)
- [ ] T029 Run `invoke format && invoke lint` (review any autoflake edits), `uv run ansible-lint`, `uv run mypy .` (no Python changes expected), `invoke tests-sanity` if Docker is available; `invoke galaxy-build` and confirm the tarball contains `roles/backup/`
- [ ] T030 Execute quickstart.md end-to-end on a Linux systemd host with Infrahub if one is available; otherwise record in the implementation report that e2e was not executed and list the follow-ups (CI wiring for `run.sh`, dependency-bump automation for the tool version)

## Dependencies

- Phase 1 → Phase 2 → US1 → (US2, US3 in either order) → Polish.
- US2 and US3 each only touch `vars/main.yml`/`tasks/main.yml` sections plus test additions; run sequentially to avoid edit conflicts in `tasks/main.yml`.
- T008, T009 parallel; T013, T015, T016 parallel; T026, T027 parallel.

## Parallel Example (US1)

```text
T008 test_validation.yml  |  T009 test_render.yml
T013 env.j2  |  T015 service.j2  |  T016 timer.j2
```

## Implementation Strategy

MVP = Phases 1–3 (scheduled local backups, validated, idempotent, secret-safe). Then US2 (S3 is mostly flag plumbing already in `create_args`), US3, docs.
