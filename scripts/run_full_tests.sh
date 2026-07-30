#!/usr/bin/env sh
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
  npm ci --no-audit --no-fund
else
  npm install --no-audit --no-fund
fi
npm run build

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  cd "$ROOT"
  docker compose config --quiet
else
  echo "SKIP: Docker is not installed; docker compose runtime test not executed."
fi
