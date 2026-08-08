#!/usr/bin/env bash
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Provides an idempotent AWS CLI guard around the deployment
# implementation so retrying a shared KMS-key recovery cannot fail when AWS
# reports that a key has already left PendingDeletion state.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMPLEMENTATION="$SCRIPT_DIR/deploy-original.sh"

[[ -x "$IMPLEMENTATION" ]] || {
  echo "Deployment implementation is missing or not executable: $IMPLEMENTATION" >&2
  exit 1
}

REAL_AWS="$(command -v aws || true)"
[[ -n "$REAL_AWS" ]] || {
  echo "aws is required" >&2
  exit 1
}

AWS_SHIM_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$AWS_SHIM_DIR"
}

trap cleanup EXIT INT TERM

export REAL_AWS

cat >"$AWS_SHIM_DIR/aws" <<'AWS_WRAPPER'
#!/usr/bin/env bash
set -uo pipefail

# cancel-key-deletion is state-sensitive. During deployment retries multiple
# secrets can share one customer-managed key. A prior secret may already have
# cancelled deletion while a subsequent describe call still observed the old
# PendingDeletion state. In that one race, AWS returns KMSInvalidStateException
# saying the key is not pending deletion. Treat that response as idempotent
# success; every other AWS error remains fatal and unchanged.
if [[ "${1:-}" == "kms" && "${2:-}" == "cancel-key-deletion" ]]; then
  set +e
  output="$("$REAL_AWS" "$@" 2>&1)"
  status="$?"
  set -e

  if [[ "$status" -eq 0 ]]; then
    if [[ -n "$output" ]]; then
      printf '%s\n' "$output"
    fi
    exit 0
  fi

  if grep -Fq 'KMSInvalidStateException' <<<"$output" &&
     grep -Fq 'is not pending deletion' <<<"$output"; then
    echo "KMS deletion was already cancelled by an earlier recovery step; continuing." >&2
    exit 0
  fi

  printf '%s\n' "$output" >&2
  exit "$status"
fi

exec "$REAL_AWS" "$@"
AWS_WRAPPER

chmod 0700 "$AWS_SHIM_DIR/aws"
export PATH="$AWS_SHIM_DIR:$PATH"

"$IMPLEMENTATION" "$@"
