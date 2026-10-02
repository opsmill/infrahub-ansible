#!/bin/sh
# Env-file round-trip (decision 11, research R11): source a rendered env file the
# way the run-now wrapper does (`set -a; . file`) and compare the sha256 of every
# value to the expected hash. Never prints a value.
# Usage: envfile_roundtrip.sh <env file> <expected file: KEY=<sha256> per line>
# POSIX sh only, so it also runs under dash (debian /bin/sh).
set -eu

env_file="$1"
expected="$2"

sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum | cut -d' ' -f1
  else
    shasum -a 256 | cut -d' ' -f1
  fi
}

failed=0
while IFS='=' read -r key want; do
  [ -n "$key" ] || continue
  # Fresh shell per key: nothing from this script leaks into the sourced environment.
  got="$(/bin/sh -c 'set -a; . "$1"; set +a; eval "v=\${$2-UNSET-$2}"; printf "%s" "$v"' \
    sh "$env_file" "$key" | sha256)"
  if [ "$got" = "$want" ]; then
    echo "ok: $key"
  else
    echo "FAIL: $key does not round-trip through /bin/sh" >&2
    failed=1
  fi
done < "$expected"

exit "$failed"
