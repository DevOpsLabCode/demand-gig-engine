#!/usr/bin/env bash
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Provisions the protected account-foundation backend through the shared global/bootstrap stack.

set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CREATE_BACKEND=true "$ROOT/scripts/bootstrap.sh" account >/dev/null

printf 'Created %s\n' "$ROOT/global/account/backend.hcl"
printf 'Next: terraform -chdir=terraform/global/account init -backend-config=backend.hcl\n'
