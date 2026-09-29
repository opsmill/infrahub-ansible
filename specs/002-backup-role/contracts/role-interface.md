# Contract: `opsmill.infrahub.backup` role interface

This is the public interface. `roles/backup/meta/argument_specs.yml`, `roles/backup/defaults/main.yml` and `docs/docs/references/roles/backup.mdx` MUST all match this table.

## Variables

| Variable | Type | Default | Choices / constraint | Maps to |
|---|---|---|---|---|
| `backup_infrahub_version` | str | `v2.3.0` | release tag | download URL |
| `backup_infrahub_tool_url` | str | `https://github.com/opsmill/infrahub-backup/releases/download/{{ backup_infrahub_version }}/infrahub-backup-linux-{{ arch }}` | — | `get_url.url` |
| `backup_infrahub_tool_checksum` | str | `sha256:https://github.com/opsmill/infrahub-backup/releases/download/{{ backup_infrahub_version }}/SHA256SUMS` | `<algo>:<hex or URL>` | `get_url.checksum` |
| `backup_infrahub_install_tool` | bool | `true` | set `false` when the binary is provisioned another way | — |
| `backup_infrahub_bin_path` | str | `/usr/local/bin/infrahub-backup` | — | install dest / ExecStart |
| `backup_infrahub_backup_directory` | str | `/var/backups/infrahub` | — | `--backup-dir` |
| `backup_infrahub_backup_directory_mode` | str | `"0700"` | — | `file.mode` |
| `backup_infrahub_config_directory` | str | `/etc/infrahub-backup` | — | env file location |
| `backup_infrahub_docker_project` | str | `infrahub` | `''` omits the flag (tool auto-detects) | `--project` |
| `backup_infrahub_force` | bool | `false` | — | `--force` |
| `backup_infrahub_neo4j_metadata` | str | `all` | `all`, `none`, `users`, `roles` | `--neo4jmetadata` |
| `backup_infrahub_exclude_taskmanager` | bool | `false` | — | `--exclude-taskmanager` |
| `backup_infrahub_log_format` | str | `text` | `text`, `json` | `--log-format` |
| `backup_infrahub_retention_days` | int | unset | ≥ 1 | `--retention-days` |
| `backup_infrahub_retention_count` | int | unset | ≥ 1 | `--retention-count` |
| `backup_infrahub_s3_upload` | bool | `false` | requires `s3_bucket` | `--s3-upload` |
| `backup_infrahub_s3_bucket` | str | unset | — | `--s3-bucket` |
| `backup_infrahub_s3_prefix` | str | unset | — | `--s3-prefix` |
| `backup_infrahub_s3_endpoint` | str | unset | URL | `--s3-endpoint` |
| `backup_infrahub_s3_region` | str | unset (tool default `us-east-1`) | — | `--s3-region` |
| `backup_infrahub_s3_keep_local` | bool | `false` | — | `--s3-keep-local` |
| `backup_infrahub_s3_access_key_id` | str | unset | `no_log`; both-or-neither with secret | env `AWS_ACCESS_KEY_ID` |
| `backup_infrahub_s3_secret_access_key` | str | unset | `no_log`; both-or-neither with id | env `AWS_SECRET_ACCESS_KEY` |
| `backup_infrahub_setup_systemd` | bool | `true` | `false` installs no units; stops+disables an existing timer only when `systemd_manage_state` is true and the timer file exists; unit files left in place | units + timer |
| `backup_infrahub_systemd_directory` | str | `/etc/systemd/system` | — | unit path |
| `backup_infrahub_systemd_manage_state` | bool | `true` | `false` = render units only | daemon-reload / timer state |
| `backup_infrahub_schedule` | str | `*-*-* 02:00:00` | systemd `OnCalendar` expression | timer `OnCalendar=` |
| `backup_infrahub_randomized_delay` | str | `"0"` | systemd time span | timer `RandomizedDelaySec=` |
| `backup_infrahub_service_user` | str | `root` | needs Docker access | service `User=` |
| `backup_infrahub_on_failure` | str | unset | systemd unit name (e.g. `notify-failure@%n.service`) | service `OnFailure=` |
| `backup_infrahub_environment` | dict | `{}` | `no_log`; extra env vars for the tool (e.g. `INFRAHUB_DB_PASSWORD`) | env file |
| `backup_infrahub_run_now` | bool | `false` | — | immediate `create` |
| `backup_infrahub_become` | bool | `true` | — | task `become` |

`--backup-dir`, `--project` (unless `docker_project` is `''`), `--log-format` and `--neo4jmetadata` are always passed with the role defaults. Optional flags whose variable is unset or `false` are omitted from the command line (tool defaults apply). `run_now` runs as `service_user` (via `become_user` when `become` is true), matching the scheduled unit.

## Files written on the host

| Path | Mode | Owner | When |
|---|---|---|---|
| `{{ bin_path }}` | 0755 | root | `install_tool` |
| `{{ backup_directory }}` | `{{ backup_directory_mode }}` | `service_user` | always |
| `{{ config_directory }}/` | 0700 | root | always |
| `{{ config_directory }}/infrahub-backup.env` | 0600 | root | always (holds credentials and `backup_infrahub_environment`; comment-only when both empty) |
| `{{ systemd_directory }}/infrahub-backup.service` | 0644 | root | `setup_systemd` |
| `{{ systemd_directory }}/infrahub-backup.timer` | 0644 | root | `setup_systemd` |

## Failure contract (before any change)

| Condition | Message contains |
|---|---|
| Wrong type / unknown choice | Ansible argument-spec error |
| `retention_days` or `retention_count` < 1 | `must be >= 1` |
| `s3_upload` true and `s3_bucket` empty | `backup_infrahub_s3_bucket is required` |
| Only one of the two S3 credentials set | `must be set together` |
| `backup_infrahub_environment` key not matching `^[A-Za-z_][A-Za-z0-9_]*$` | `invalid environment variable name` (offending keys only, never values) |
| An S3 credential or `backup_infrahub_environment` value contains a newline, CR, `\`, `"`, `'`, `$`, or leading/trailing whitespace | `contains characters that systemd EnvironmentFile cannot represent safely` (variable/key name only, never the value) |
| `install_tool` true, `tool_url` set, `tool_checksum` unset | `backup_infrahub_tool_checksum is required when backup_infrahub_tool_url is set` |
| `install_tool` true and arch not x86_64/aarch64/arm64 | `Unsupported architecture` |

## Out of contract

Redact, restore, standalone prune, `--sleep`, Kubernetes.
