#!/usr/bin/env bash
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Runs formatting, initialization, validation, linting, security scanning, Go tests, and shell checks for the Terraform framework.
# Execution model: fail fast, validate prerequisites, run each documented phase, and surface errors.

set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Run the Terraform operation for the selected working directory and environment.
terraform -chdir="$ROOT" fmt -recursive
# Run the Terraform operation for the selected working directory and environment.
terraform -chdir="$ROOT" fmt -check -recursive
# Run the Terraform operation for the selected working directory and environment.
terraform -chdir="$ROOT" init -backend=false -input=false
# Run the Terraform operation for the selected working directory and environment.
terraform -chdir="$ROOT" validate
if command -v tflint >/dev/null; then
  tflint --chdir="$ROOT" --recursive
fi
if command -v checkov >/dev/null; then
  checkov -d "$ROOT" --framework terraform --compact
fi
(cd "$ROOT/tests" && go test -race -count=1 -v ./...)
