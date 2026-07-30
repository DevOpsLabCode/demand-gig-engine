#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python -m pip install --requirement security-requirements.txt

checkov --directory . \
  --framework terraform cloudformation kubernetes helm bicep arm serverless dockerfile github_actions secrets \
  --skip-path '(^|/)docs/' \
  --skip-path '(^|/)screenshots/' \
  --skip-path '(^|/)validation/' \
  --skip-path '(^|/)__pycache__/' \
  --skip-check CKV_GHA_5,CKV_GHA_6 \
  --compact \
  --soft-fail \
  --hard-fail-on HIGH

pip-audit --requirement backend/requirements.txt --strict --desc

bandit --recursive backend \
  --exclude backend/gigs/tests,backend/integrations/vibesmeet/tests,backend/gigs/migrations \
  --severity-level high \
  --confidence-level medium

(
  cd frontend
  npm install --package-lock-only --ignore-scripts
  npm audit --omit=dev --audit-level=high
)
