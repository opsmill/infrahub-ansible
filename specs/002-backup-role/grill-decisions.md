# Grill Decisions: Backup Role — Iteration 2

**Date**: 2026-09-30 · **Decided by**: Pierrick Thomas (grilling session over the iteration-1 implementation) · **Supersedes** conflicting parts of spec.md / research.md / contracts from iteration 1.

## Principles

1. **Thin wrapper** — the role exposes only what `infrahub-backup` can do; no extra transfer, notification or scheduling logic beyond systemd wiring.
2. **Tool defaults** — the role uses the tool's own default for each tool flag. Exceptions: `retention_count` (7), `backup_directory` (`/var/backups/infrahub`), schedule (daily 02:00).

## Decisions

| # | Topic | Decision | vs iteration 1 |
|---|---|---|---|
| 1 | Targets | Docker Compose only; Kubernetes in a later iteration | same |
| 2 | Modularity | Add `backup_infrahub_platform` (default `docker`, choices `[docker]`). Docker-specific tasks move under `tasks/docker/`; `tasks/main.yml` validates shared inputs then includes `tasks/{{ platform }}/main.yml`. Shared options stay platform-neutral; `create_args` builder stays shared (usable later as Helm `extraArgs`) | **change** |
| 3 | Mechanism | Wrap `infrahub-backup` | same |
| 4 | Remote | S3-compatible only (tool-native). Document NFS = mount + point `backup_directory` at it | docs |
| 5 | Retention | `backup_infrahub_retention_count` default `7`; `null` disables; `retention_days` stays unset. Document union semantics, newest-always-kept floor, S3 `ListBucket`+`DeleteObject` | **change** |
| 6 | Running tasks | `force: false` (tool default) | same |
| 7 | Tool defaults | `docker_project`, `log_format`, `neo4j_metadata` default unset → flag omitted → tool default/auto-detect. `backup_directory` kept and always passed. Document that multi-project hosts must set `docker_project` | **change** |
| 8 | Schedule | Daily 02:00 host time (matches tool docs' cron example and Helm chart example). Document Community Edition = offline backup (Infrahub stopped for the dump) vs Enterprise = online (no downtime) | docs |
| 9 | Encryption | Expose `backup_infrahub_encrypt` (bool → `--encrypt`, built-in OpsMill key — only OpsMill can decrypt) and `backup_infrahub_encrypt_key` (path on host to a public key → `--encrypt-key`, implies encrypt). Operator places the key file. Plakar backend (`--backend`/`--repo`) NOT exposed | **change** |
| 10 | Run now | Keep `backup_infrahub_run_now` | same |
| 11 | Special chars | Drop the character rejection. Values must round-trip exactly into the scheduled run and the run-now run: render the env file so systemd reads back the exact value, and make run-now read the same file with the same semantics | **change** |
| 12 | User | root by default; `service_user` override; document non-root needs `docker` group + owns backup dir; role does not create users | same |
| 13 | Failure hook | **Drop** `backup_infrahub_on_failure` | **change** |
| 14 | Restore | Out of scope; link tool restore docs | same |
| 15 | Tool source | GitHub release, pinned, checksum-verified | same |
| 16 | Redact / sleep | Not exposed. Docs explain redact scrambles the LIVE database and show the manual throwaway-instance flow with the tool | docs |
| 17 | CI | Add a CI job running `tests/roles/backup/run.sh` in this PR (governance gate "CI changes" — approved) | **change** |

## Open (assumed)

- `--encrypt` / `--encrypt-key` exist in tool v2.3.0 (verified in source at tag `v2.3.0`) but are absent from published docs — confirm readiness with tool maintainers.
- CHANGELOG version (top v1.9.0 vs galaxy 1.8.3) — stays `Unreleased`.
- Encryption public key is placed on the host by the operator, not by the role.
