#!/usr/bin/env sh
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Runs application-focused checks, Django tests and coverage, frontend builds, and Docker Compose validation.
# Execution model: fail fast, validate prerequisites, run each documented phase, and surface errors.

set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON=${PYTHON:-python}

cd "$ROOT"
"$PYTHON" scripts/static_checks.py
"$PYTHON" scripts/validate_workflows.py
bash -n scripts/run_full_tests.sh
bash -n scripts/run_all_tests.sh
bash -n scripts/security_scan.sh

cd "$ROOT/backend"
DEBUG=true "$PYTHON" manage.py check
DEBUG=true "$PYTHON" manage.py makemigrations --check --dry-run
DEBUG=true "$PYTHON" manage.py migrate --noinput

cd "$ROOT"
"$PYTHON" -m flake8 backend scripts \
  --count \
  --select=E9,F63,F7,F82 \
  --show-source \
  --statistics
DEBUG=true DJANGO_SETTINGS_MODULE=config.settings PYTHONPATH=backend \
  "$PYTHON" -m pytest backend -v

cd "$ROOT/frontend"
if [ -f package-lock.json ]; then
  # Install, validate, or build the frontend assets for this phase.
  npm ci --no-audit --no-fund
else
  # Install, validate, or build the frontend assets for this phase.
  npm install --no-audit --no-fund
fi
# Install, validate, or build the frontend assets for this phase.
npm run build

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  cd "$ROOT"
  # Build, tag, publish, or inspect the container artifact required by this deployment phase.
  docker compose config --quiet
else
  echo "SKIP: Docker is not installed; docker compose runtime test not executed."
fi
