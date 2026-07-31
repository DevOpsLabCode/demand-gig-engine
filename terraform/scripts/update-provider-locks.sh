#!/usr/bin/env bash
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Regenerates signed, multi-platform Terraform provider dependency lock files for every independent root.

set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLATFORMS=(
  "linux_amd64"
  "linux_arm64"
  "darwin_amd64"
  "darwin_arm64"
)
ROOTS=(
  "terraform"
  "terraform/global/bootstrap"
  "terraform/global/account"
)

if ! command -v terraform >/dev/null 2>&1; then
  echo "Terraform CLI is required. Install the repository-pinned Terraform version first." >&2
  exit 1
fi

platform_args=()
for platform in "${PLATFORMS[@]}"; do
  platform_args+=("-platform=${platform}")
done

for relative_root in "${ROOTS[@]}"; do
  absolute_root="${REPOSITORY_ROOT}/${relative_root}"
  echo "Updating provider lock file for ${relative_root}"
  terraform -chdir="${absolute_root}" providers lock "${platform_args[@]}"
done

cat <<'MESSAGE'

Provider lock files updated for all Terraform roots.
Review provider versions, signer information, and checksums, then commit:
  terraform/.terraform.lock.hcl
  terraform/global/bootstrap/.terraform.lock.hcl
  terraform/global/account/.terraform.lock.hcl
MESSAGE
