#!/usr/bin/env bash
# Backup role tests: validation, render x2 (idempotency), run-now (fake tool), exact
# secret round-trip (decision 11) and secrecy (SC-004) of every -vvv log.
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

# Adversarial secrets (decision 11): every character the env file must escape, plus
# leading/trailing whitespace. Written as YAML single-quoted scalars so Ansible gets
# the exact bytes; expected.txt holds KEY=<sha256> of the same bytes (never values).
# Each secret keeps $SENTINEL as a literal substring for the leak grep below.
uv run --project "$REPO" python - "$TMP" "$SENTINEL" <<'EOF'
import hashlib
import sys

tmp, sentinel = sys.argv[1], sys.argv[2]
values = {
    "AWS_ACCESS_KEY_ID": "AKIATEST",
    "AWS_SECRET_ACCESS_KEY": r""" SENTINEL-SECRET-e3b0c442 a"b\c$HOME`x'y """,
    "INFRAHUB_DB_PASSWORD": r"""  $(id) \\$ "q" 'z' SENTINEL-SECRET-e3b0c442""",
}
assert sentinel in values["AWS_SECRET_ACCESS_KEY"]
assert sentinel in values["INFRAHUB_DB_PASSWORD"]


def sq(value):
    return "'" + value.replace("'", "''") + "'"


with open(f"{tmp}/secrets.yml", "w", encoding="utf-8") as f:
    f.write(f"backup_infrahub_s3_access_key_id: {sq(values['AWS_ACCESS_KEY_ID'])}\n")
    f.write(f"backup_infrahub_s3_secret_access_key: {sq(values['AWS_SECRET_ACCESS_KEY'])}\n")
    f.write("backup_infrahub_environment:\n")
    f.write(f"  INFRAHUB_DB_PASSWORD: {sq(values['INFRAHUB_DB_PASSWORD'])}\n")
with open(f"{tmp}/expected.txt", "w", encoding="utf-8") as f:
    for key in sorted(values):
        f.write(f"{key}={hashlib.sha256(values[key].encode()).hexdigest()}\n")
EOF

echo "==> test_validation.yml"
playbook "$HERE/test_validation.yml" -vvv 2>&1 | tee "$TMP/validation.log"

for run in 1 2; do
  echo "==> test_render.yml (run $run)"
  playbook "$HERE/test_render.yml" -vvv --diff \
    -e "test_root=$TMP" \
    -e "@$TMP/secrets.yml" \
    2>&1 | tee "$TMP/run$run.log"
done

# Separate playbook: run-now always reports changed, so it cannot share the
# idempotency check. Same secrets as the render runs, so no_log is active.
echo "==> test_run_now.yml"
playbook "$HERE/test_run_now.yml" -vvv --diff \
  -e "test_root=$TMP" \
  -e "@$TMP/secrets.yml" \
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

# Scheduled-path parser, sh side: the rendered file sourced by /bin/sh yields the
# exact values. The systemd side is research R11 (verified separately).
echo "==> env file round-trip (/bin/sh)"
sh "$HERE/envfile_roundtrip.sh" "$ENV_FILE" "$TMP/expected.txt"

# Run-now path: the fake tool recorded KEY=<sha256> of what it received.
echo "==> run-now received values"
if ! diff -u "$TMP/expected.txt" <(sort "$TMP/runnow/env.txt") >&2; then
  echo "FAIL: run-now tool did not receive the exact secret values" >&2
  exit 1
fi
echo "ok: run-now hashes match"

echo "PASS: backup role tests"
