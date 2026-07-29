#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

python "$ROOT/scripts/static_checks.py"

cd "$ROOT/backend"
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py test --verbosity 2

cd "$ROOT/frontend"
npm install --no-audit --no-fund
npm run build

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  cd "$ROOT"
  docker compose config --quiet
else
  echo "SKIP: Docker is not installed; docker compose runtime test not executed."
fi
