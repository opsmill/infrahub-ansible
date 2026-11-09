# Feature Specification: Backup Role for Infrahub Instances

**Feature Branch**: `issue-163` (spec directory `002-backup-role`)

**Created**: 2026-09-29

**Status**: Iteration 2 (updated 2026-09-30 from [grill-decisions.md](grill-decisions.md))

**Input**: GitHub issue [opsmill/infrahub-ansible#163](https://github.com/opsmill/infrahub-ansible/issues/163) — "feature: Add role to backup an infrahub instance". *"Similar to the install role, I would like to have a role to ease the backup. Use case: backup an Infrahub Instance locally/remotely; ease to configure systemd service."*

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Schedule recurring local backups with one role (Priority: P1)

An operator who installed Infrahub on a Docker Compose host (typically with the collection's `install` role) adds a `backup` role to the same play. After one run, the host has the OpsMill backup tool installed and a systemd-managed schedule that writes backup archives to a local directory on a recurring basis, pruning old archives so the disk does not fill up.

**Why this priority**: This is the core of the issue — "ease the backup" and "ease to configure systemd service". A scheduled local backup is the minimum viable disaster-recovery routine and has no external dependency.

**Independent Test**: Apply the role with only default variables to a host running Infrahub under Docker Compose; confirm the backup tool is present, a timer is enabled and active with the expected schedule, and triggering the service once produces a backup archive in the configured directory.

**Acceptance Scenarios**:

1. **Given** a host running Infrahub under Docker Compose, **When** the role is applied with default variables, **Then** the backup tool is installed, the backup directory exists, and a systemd timer is enabled and started for a daily backup.
2. **Given** the role was applied, **When** the backup service is triggered manually, **Then** a new backup archive appears in the backup directory and the service exits successfully.
3. **Given** the role was applied once, **When** it is applied again with the same variables, **Then** the run reports no changes.
4. **Given** a retention policy is configured (number of days and/or number of archives), **When** scheduled backups run over time, **Then** archives outside the policy are removed after each successful backup.
5. **Given** the operator changes the schedule variable, **When** the role is re-applied, **Then** the timer reflects the new schedule and systemd is reloaded.

---

### User Story 2 - Send backups to remote object storage (Priority: P2)

An operator who needs off-host copies configures S3-compatible remote storage (AWS S3 or a self-hosted equivalent such as MinIO) through role variables, including bucket, path prefix, endpoint, region and credentials. Every scheduled backup is then uploaded to that remote location, optionally keeping a local copy as well. Archives can optionally be encrypted, either with OpsMill's built-in key (for sharing with OpsMill support) or with the operator's own public key.

**Why this priority**: The issue explicitly asks for "locally/remotely". A local-only backup does not survive loss of the host, so remote storage is the second most valuable capability, but it depends on the operator having object storage available.

**Independent Test**: Apply the role with remote storage variables pointing at a test bucket; trigger the backup service; confirm the archive lands under the configured prefix and that the local copy is kept or removed according to the configured option.

**Acceptance Scenarios**:

1. **Given** remote storage variables are set, **When** a backup runs, **Then** the archive is uploaded to the configured bucket and prefix.
2. **Given** "keep local copy" is enabled, **When** a backup with remote upload runs, **Then** the archive exists both locally and remotely; when disabled, only remotely.
3. **Given** remote storage credentials are provided, **When** the role runs with verbose output, **Then** the credential values never appear in the Ansible output, and the file that stores them on the host is readable only by its owner.
4. **Given** remote upload is enabled but no bucket is set, **When** the role runs, **Then** it fails early with a clear message before changing the host.
5. **Given** an encryption public key path is configured, **When** a backup runs, **Then** the archive is encrypted with that key; **Given** built-in encryption is enabled instead, **Then** the archive is encrypted with the tool's built-in OpsMill key.
6. **Given** a credential or extra environment value containing quotes, `\`, `$` or surrounding spaces, **When** the scheduled run and the on-demand run execute, **Then** both receive exactly the configured value.

---

### User Story 3 - Take a backup on demand from a playbook (Priority: P3)

An operator about to upgrade Infrahub wants a backup taken right now, as a step in their upgrade playbook, rather than waiting for the next scheduled run. They apply the role with an "run backup now" option enabled (with or without the scheduled timer) and the play only continues once the backup has completed successfully.

**Why this priority**: Pre-upgrade backups are a common operational need and reuse everything built for Stories 1 and 2, but scheduling is the primary ask.

**Independent Test**: Apply the role with the on-demand option enabled and the timer disabled; confirm a new archive exists when the play finishes and no timer was installed.

**Acceptance Scenarios**:

1. **Given** the on-demand option is enabled, **When** the role runs, **Then** exactly one backup is created during the run and the run reports a change.
2. **Given** the on-demand option is enabled and the backup fails (for example, tasks are running and forcing is not allowed), **When** the role runs, **Then** the play fails with the backup tool's error message.
3. **Given** systemd scheduling is disabled, **When** the role runs, **Then** no service or timer unit is installed, and the backup tool is still installed.

---

### Edge Cases

- The host architecture has no published backup tool build (neither x86_64 nor aarch64): the role fails with an explicit "unsupported architecture" message.
- Multiple Infrahub Compose projects run on the same host: by default the role passes no project and the tool auto-detects, which can be ambiguous; the operator must then set the project name (documented).
- Infrahub tasks are running when the scheduled backup starts: by default the backup refuses (the tool's safe behaviour); the operator may opt in to forcing.
- Community Edition is backed up offline (Infrahub services stopped for the dump) while Enterprise is backed up online: documented so Community operators schedule the timer in a maintenance window.
- A retention value of `0` or a negative number: rejected by the role before anything is written, rather than deferred to a failing nightly run.
- The host was powered off at the scheduled time: the missed backup runs at next boot.
- Operator disables scheduling after previously enabling it: the timer is stopped and disabled, so backups stop.
- The redact option of the backup tool scrambles the live database and is deliberately not exposed; the docs explain the manual flow on a throwaway instance.
- A credential or environment value containing a newline cannot be represented in an environment file: rejected before any change, naming the variable only.
- A platform other than `docker` is requested: rejected by the argument specification.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The collection MUST ship a role named `backup` (fully qualified `opsmill.infrahub.backup`), structured and documented consistently with the existing `install` role (defaults, argument specification, metadata, README-level docs page).
- **FR-002**: The role MUST install the OpsMill `infrahub-backup` command-line tool on the target host, at a pinned, operator-overridable version, selecting the correct build for the host's architecture.
- **FR-003**: The role MUST verify the downloaded tool against its published checksum before installing it.
- **FR-004**: Re-applying the role with the same variables MUST report no changes (idempotency), including the tool installation, configuration and systemd units.
- **FR-005**: The role MUST create the local backup directory with restrictive permissions if it does not exist.
- **FR-006**: The role MUST let the operator configure: backup directory, Docker Compose project name, whether to force a backup while tasks are running, which Neo4j metadata to include, whether to exclude the task-manager database, and log format. Except for the backup directory, each option MUST default to the tool's own default by omitting the corresponding flag when unset.
- **FR-007**: The role MUST apply a retention policy after each successful backup: by count (default 7 archives, disable with `null`) and optionally by age (days, unset by default); values below 1 MUST be rejected at role-validation time.
- **FR-008**: The role MUST support uploading each backup to S3-compatible remote storage with configurable bucket, prefix, endpoint, region and "keep local copy" option.
- **FR-009**: Remote storage credentials, and any extra tool environment variables the operator supplies (for example database credentials when auto-detection fails), MUST be accepted as role variables, MUST NOT appear in Ansible output, and MUST be stored on the host only in a file readable by its owner (mode 0600 or stricter), and MUST reach both the scheduled and the on-demand backup byte-for-byte unchanged, including quotes, backslashes, `$` and surrounding whitespace (only newlines are rejected). When credentials are not set, the role MUST rely on the tool's standard credential chain (for example an instance role).
- **FR-010**: The role MUST, by default, install a systemd service and timer that run the backup on a configurable schedule (default: daily at 02:00 host time), catching up missed runs after downtime.
- **FR-011**: The operator MUST be able to disable systemd setup; disabling it after a previous enablement MUST stop and disable the timer.
- **FR-012**: The role MUST offer an opt-in option to run one backup immediately during the play, failing the play if the backup fails.
- **FR-013**: Changes to schedule or backup configuration MUST take effect on re-apply without manual steps (systemd reloaded, timer restarted when needed).
- **FR-014**: The role MUST validate its inputs through an argument specification so invalid types or choices fail before any change is made.
- **FR-015**: The role MUST NOT expose the backup tool's redact option, `--sleep`, the Plakar backend, or restore operations; redact and restore MUST be explained in the docs.
- **FR-016**: The role MUST be documented on the collection's documentation site alongside the `install` role, including an example playbook combining `install` and `backup`, how to check that scheduled backups succeed, a pointer to the tool's restore procedure, the S3 behaviours operators must know (local copy removed after upload unless kept; pruning remote archives needs delete permission), and a changelog entry.
- **FR-017**: The role MUST support archive encryption: with the tool's built-in OpsMill key, or with an operator-supplied public key file on the host. The docs MUST state that built-in-key archives can only be decrypted by OpsMill.
- **FR-018**: The role MUST take a deployment platform option, defaulting to Docker Compose and currently accepting only it, so another platform can be added later without breaking existing playbooks.
- **FR-019**: The role's test suite MUST run in the collection's CI on every pull request.

### Key Entities

- **Backup tool**: The OpsMill `infrahub-backup` binary installed on the host; identified by version and architecture.
- **Backup configuration**: The set of operator choices (directory, project, retention, remote storage, flags) rendered onto the host and consumed by every backup run, whether scheduled or on demand.
- **Remote storage credentials**: Secret access key pair for S3-compatible storage; sensitive.
- **Schedule**: The systemd service + timer pair defining when backups run.
- **Backup archive**: The file produced by one backup run, stored locally and/or remotely; its content and format are owned by the backup tool, not by this role.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator with a running Docker Compose Infrahub instance gets scheduled daily backups by adding one role and zero required variables to their play.
- **SC-002**: A second application of the role with unchanged variables reports 0 changed tasks.
- **SC-003**: Enabling remote storage requires setting at most 3 variables (bucket plus credentials) when defaults for region/endpoint suit AWS.
- **SC-004**: No secret value supplied to the role appears in Ansible output at any verbosity level.
- **SC-005**: Invalid input (unknown metadata choice, retention below 1, remote upload without bucket, unknown platform) fails the play before any host change, 100% of the time.
- **SC-007**: A secret containing quotes, `\`, `$` and surrounding spaces is received unchanged by both the scheduled and the on-demand backup.
- **SC-006**: Every role variable is described in the published documentation, with its default.

## Assumptions

- Target deployment is Docker Compose on a Linux systemd host, matching the `install` role. Kubernetes is deferred to a later iteration (the role is structured per platform to allow it); the Infrahub Helm chart already offers an in-cluster backup subchart.
- The role delegates backup mechanics (database dumps, archive format, S3 upload, retention pruning) to the official `infrahub-backup` tool rather than reimplementing them.
- The tool is downloaded from its official GitHub release, which publishes Linux amd64/arm64 builds and a checksum file; hosts need outbound access to it (air-gapped installs can override the download URL).
- "Remotely" is interpreted as S3-compatible object storage, which the tool supports natively. Other transports (SCP, rsync, NFS) are out of scope; an NFS mount can be used simply by pointing the backup directory at it.
- Restore is out of scope for this role — it is an interactive, destructive operation better run by hand or in a separate future role.
- Backups run as root by default (the tool needs Docker access); operators may override the service user.
- Docker Compose project, log format and Neo4j metadata default to the tool's behaviour (flag omitted).
- Compatibility between the backup tool and a given Infrahub version is owned by the tool; the role pins a tool version and lets operators override it.
- Role variables use a `backup_infrahub_` prefix, mirroring the `install_infrahub_` convention.
- No failure-notification hook: operators check `systemctl list-timers` / `journalctl` (iteration-1 `on_failure` removed).
- The encryption public key file is placed on the host by the operator.
