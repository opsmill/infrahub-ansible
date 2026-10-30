# Spec/Ask Alignment Check: 002-backup-role

## Source

- GitHub issue [opsmill/infrahub-ansible#163](https://github.com/opsmill/infrahub-ansible/issues/163), fetched with `gh issue view` on 2026-09-29 (no comments).
- Ask: "Similar to the install role, I would like to have a role to ease the backup." Use case: "backup an Infrahub Instance locally/remotely; ease to configure systemd service." Feature type: New Module. Reporter's Infrahub version: 1.1.5.

## Verdict

⚠️ **MINOR DRIFT (proceeding)**

## Findings

| Severity | Category | PRD reference | Spec reference | Description |
|---|---|---|---|---|
| Minor | added | — | US3, FR-012 | On-demand "run backup now" option not in the issue. Opt-in (default off), reuses the same command; supports the "ease the backup" intent. Kept. |
| Minor | added | — | FR-007 | Retention policy not in the issue. Needed so a scheduled backup does not fill the disk; delegated to the tool; optional. Kept. |
| Minor | added | — | FR-017 | Failure hook (`OnFailure=`) from critique E1. Optional; makes the systemd schedule usable in practice. Kept. |
| Minor | changed (narrowed) | "remotely" | Assumptions, FR-008 | "Remotely" interpreted as S3-compatible storage (tool-native). SCP/rsync excluded; NFS works via the backup directory. Reasonable interpretation, documented. |
| Info | — | "Similar to the install role" | FR-001, plan | Layout, naming (`backup_infrahub_*`), systemd approach and docs page mirror `roles/install`. Aligned. |
| Info | — | "ease to configure systemd service" | FR-010/011/013 | Covered: service + timer by default, configurable schedule, opt-out. Aligned. |
| Info | — | Infrahub 1.1.5 | Assumptions | Tool ↔ Infrahub compatibility owned by the tool; version overridable. Not verified against 1.1.5. |

No requirement from the issue is missing, softened or contradicted.

## Action

Proceed. No remediation passes run (counter: 0).
