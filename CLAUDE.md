@AGENTS.md

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->

## Active Technologies

- Ansible YAML + Jinja2; ansible-core >=2.19.0 (repo `meta/runtime.yml`); no Python changes. + `ansible.builtin` only (`get_url`, `template`, `file`, `systemd_service`, `command`, `assert`, `stat`). Runtime: `infrahub-backup` v2.3.0 binary on the target; Docker Engine + Compose v2 (as for `install`). (002-backup-role)
- Host files only (binary, env file, units, backup directory). (002-backup-role)
- Python >=3.11, <3.15 (`pyproject.toml`) + `ansible-core>=2.19.0`; `infrahub-sdk[all]>=1.19.0,<2.0` (synchronous client only) (001-inventory-fetch-performance)

## Recent Changes

- 001-inventory-fetch-performance: Cut dynamic inventory fetch round-trips — query projection, bounded peer fetches, batched refill
