# Data Model: Backup Role (002-backup-role)

No persistent data owned by the role. The "entities" are host artefacts and the variables that produce them. Full variable table: [contracts/role-interface.md](contracts/role-interface.md).

## Entities

### BackupTool

- Fields: `version` (release tag), `arch` (`amd64` | `arm64`, derived from `ansible_facts.architecture`), `bin_path`, `url`, `checksum`.
- Invariant: installed binary's SHA-256 equals the release `SHA256SUMS` entry for `infrahub-backup-linux-<arch>`.
- Transition: version change → checksum mismatch → re-download (upgrade). Same version → no-op.

### BackupConfiguration

- Derived value `backup_infrahub_create_args` (list of CLI tokens, built in `roles/backup/vars/main.yml`):
  `--backup-dir <dir>`, `--project <p>`, `--log-format <f>`, `create`, `--neo4jmetadata <m>`, plus conditional `--force`, `--exclude-taskmanager`, `--retention-days N`, `--retention-count N`, `--s3-upload`, `--s3-bucket`, `--s3-prefix`, `--s3-endpoint`, `--s3-region`, `--s3-keep-local`.
  - Global flags (`--backup-dir`, `--project`, `--log-format`, `--s3-*` location flags) are placed before `create`, per the tool's `infrahub-backup [global-flags] <command> [flags]` syntax; create-only flags after.
- Consumed by: service `ExecStart`, on-demand command. Single source of truth.
- Validation: see failure contract.

### RemoteStorageCredentials

- Fields: `access_key_id`, `secret_access_key` (both-or-neither).
- Stored only in `infrahub-backup.env` (0600). Never in unit files, never in logs/diff.

### Schedule

- `infrahub-backup.service` (oneshot, not enabled) + `infrahub-backup.timer` (enabled, started).
- States: *absent* → (setup_systemd) → *active* → (setup_systemd=false) → *disabled/stopped* (files kept).
- Config change on active timer → daemon-reload + timer restart via handlers.

### BackupArchive

- `infrahub_backup_<YYYYMMDD_HHMMSS>.tar.gz` produced by the tool; format and retention owned by the tool.
