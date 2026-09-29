#!/usr/bin/env bash
# Backup role tests: validation, render x2 (idempotency), run-now (fake tool) and
# secrecy (SC-004) of every -vvv log.
# The secrecy check lives here because a play cannot observe its own stdout (critique E3).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HERE="$REPO/tests/roles/backup"
SENTINEL="SENTINEL-SECRET-e3b0c442"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

export ANSIBLE_ROLES_PATH="$REPO/roles"
export ANSIBLE_NOCOLOR=1

playbook() {
  uv run --project "$REPO" ansible-playbook -i localhost, -c local "$@"
}

echo "==> test_validation.yml"
playbook "$HERE/test_validation.yml" -vvv 2>&1 | tee "$TMP/validation.log"

for run in 1 2; do
  echo "==> test_render.yml (run $run)"
  playbook "$HERE/test_render.yml" -vvv --diff \
    -e "test_root=$TMP" \
    -e backup_infrahub_s3_access_key_id=AKIATEST \
    -e "backup_infrahub_s3_secret_access_key=$SENTINEL" \
    -e "{\"backup_infrahub_environment\": {\"INFRAHUB_DB_PASSWORD\": \"$SENTINEL\"}}" \
    2>&1 | tee "$TMP/run$run.log"
done

# Separate playbook: run-now always reports changed, so it cannot share the
# idempotency check. Same secrets as the render runs, so no_log is active.
echo "==> test_run_now.yml"
playbook "$HERE/test_run_now.yml" -vvv --diff \
  -e "test_root=$TMP" \
  -e backup_infrahub_s3_access_key_id=AKIATEST \
  -e "backup_infrahub_s3_secret_access_key=$SENTINEL" \
  -e "{\"backup_infrahub_environment\": {\"INFRAHUB_DB_PASSWORD\": \"$SENTINEL\"}}" \
  2>&1 | tee "$TMP/runnow.log"

for log in validation run1 run2 runnow; do
  if grep -q "$SENTINEL" "$TMP/$log.log"; then
    echo "FAIL: secret leaked in $log output (-vvv)" >&2
    exit 1
  fi
done

if ! grep -Eq '^localhost[[:space:]]*:.*[[:space:]]changed=0[[:space:]]' "$TMP/run2.log"; then
  echo "FAIL: second render run is not idempotent (expected changed=0)" >&2
  grep -E '^localhost[[:space:]]*:' "$TMP/run2.log" >&2 || true
  exit 1
fi

ENV_FILE="$TMP/default/etc/infrahub-backup.env"
if ! grep -q "$SENTINEL" "$ENV_FILE"; then
  echo "FAIL: secret not stored in $ENV_FILE" >&2
  exit 1
fi

echo "PASS: backup role tests"
