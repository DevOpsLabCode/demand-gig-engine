#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_ROOT="$(cd "$ROOT/.." && pwd)"
python3 "$REPOSITORY_ROOT/scripts/validate_terraform_contracts.py"
terraform -chdir="$ROOT" fmt -recursive
terraform -chdir="$ROOT" fmt -check -recursive
terraform -chdir="$ROOT" init -backend=false -input=false
terraform -chdir="$ROOT" validate
if command -v tflint >/dev/null; then
  tflint --chdir="$ROOT" --recursive
fi
if command -v checkov >/dev/null; then
  checkov -d "$ROOT" --framework terraform --compact
fi
(cd "$ROOT/tests" && go test -race -count=1 -v ./...)
