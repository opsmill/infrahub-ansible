# Quickstart: Backup Role (002-backup-role)

## Local checks (no Infrahub needed)

```bash
uv run ansible-lint roles/backup
tests/roles/backup/run.sh   # validation + render (x2, idempotency) + -vvv --diff secret grep
```

Expected: lint clean; both playbooks end with `failed=0`. `run.sh` exits 0 only if validation cases fail as expected, the second render pass reports `changed=0`, and the sentinel secret never appears in `-vvv --diff` output.

## End-to-end (Linux systemd host with Infrahub on Docker Compose)

```yaml title="backup_infrahub.yml"
- name: Install and back up Infrahub
  hosts: infrahub_servers
  become: true
  roles:
    - role: opsmill.infrahub.install
    - role: opsmill.infrahub.backup
      vars:
        backup_infrahub_retention_count: 14
        backup_infrahub_run_now: true
```

```bash
ansible-playbook -i inventory.yml backup_infrahub.yml        # changed > 0, one archive created
ansible-playbook -i inventory.yml backup_infrahub.yml -e backup_infrahub_run_now=false   # changed=0
ssh host systemctl list-timers infrahub-backup.timer          # next run listed
ssh host sudo systemctl start infrahub-backup.service && ls /var/backups/infrahub
```

Remote (MinIO/S3):

```yaml
backup_infrahub_s3_upload: true
backup_infrahub_s3_bucket: infrahub-backups
backup_infrahub_s3_endpoint: http://minio.local:9000
backup_infrahub_s3_access_key_id: "{{ vault_s3_key }}"
backup_infrahub_s3_secret_access_key: "{{ vault_s3_secret }}"
```

Verify: `ansible-playbook ... -vvv --diff | grep -c "{{ secret }}"` → `0`; `stat -c %a /etc/infrahub-backup/infrahub-backup.env` → `600`.
