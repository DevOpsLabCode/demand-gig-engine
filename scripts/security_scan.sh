#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python -m pip install --requirement security-requirements.txt
python scripts/validate_workflows.py || workflow_status=$?
workflow_status=${workflow_status:-0}

# Full report across all supported repository configuration. This is
# informational; the focused policy gate below is blocking.
checkov --directory . \
  --framework terraform cloudformation kubernetes helm bicep arm serverless dockerfile github_actions openapi secrets \
  --skip-path '(^|/)docs/' \
  --skip-path '(^|/)screenshots/' \
  --skip-path '(^|/)validation/' \
  --skip-path '(^|/)node_modules/' \
  --skip-path '(^|/)__pycache__/' \
  --skip-path '(^|/)\.env\.example$' \
  --skip-check CKV_GHA_5,CKV_GHA_6 \
  --compact \
  --soft-fail || checkov_report_status=$?
checkov_report_status=${checkov_report_status:-0}

# Blocking Checkov gate that works without a Prisma Cloud API key.
checkov --directory . \
  --framework dockerfile github_actions secrets \
  --enable-secret-scan-all-files \
  --skip-path '(^|/)docs/' \
  --skip-path '(^|/)screenshots/' \
  --skip-path '(^|/)validation/' \
  --skip-path '(^|/)node_modules/' \
  --skip-path '(^|/)__pycache__/' \
  --skip-path '(^|/)\.env\.example$' \
  --skip-check CKV_GHA_5,CKV_GHA_6 \
  --compact || checkov_status=$?
checkov_status=${checkov_status:-0}

pip-audit --requirement backend/requirements.txt --strict --desc || pip_audit_status=$?
pip_audit_status=${pip_audit_status:-0}

bandit --recursive backend \
  --exclude backend/gigs/tests,backend/integrations/vibesmeet/tests,backend/gigs/migrations \
  --severity-level high \
  --confidence-level medium || bandit_status=$?
bandit_status=${bandit_status:-0}

(
  cd frontend
  npm install --package-lock-only --ignore-scripts --no-fund --no-audit
  npm audit --omit=dev --audit-level=high
) || npm_status=$?
npm_status=${npm_status:-0}

printf '\nSecurity scan exit codes: workflows=%s checkov-report=%s checkov-gate=%s pip-audit=%s bandit=%s npm=%s\n' \
  "$workflow_status" "$checkov_report_status" "$checkov_status" \
  "$pip_audit_status" "$bandit_status" "$npm_status"

if (( workflow_status || checkov_report_status || checkov_status || pip_audit_status || bandit_status || npm_status )); then
  exit 1
fi
