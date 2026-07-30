#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$repo_root" ]]; then
  echo "ERROR: Run this script from inside the demand-gig-engine Git repository." >&2
  exit 1
fi
cd "$repo_root"

mkdir -p .github/workflows backend

cat > .github/workflows/python-package.yml <<'YAML'
name: Backend tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: backend-tests-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    name: Python ${{ matrix.python-version }}
    runs-on: ubuntu-latest
    timeout-minutes: 15

    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - name: Check out repository
        uses: actions/checkout@v5

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v7
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
          cache-dependency-path: |
            requirements.txt
            backend/requirements.txt
            backend/requirements-dev.txt

      - name: Install project dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install --requirement requirements.txt
          python -m pip check

      - name: Verify Django test environment
        run: |
          python -c "import django; print('Django', django.get_version())"
          python -c "import pytest_django; print('pytest-django installed')"
          python -m pytest --version

      - name: Check Django configuration and migrations
        working-directory: backend
        env:
          SECRET_KEY: ci-test-secret-key
          DEBUG: "false"
        run: |
          python manage.py check
          python manage.py makemigrations --check --dry-run

      - name: Check Python syntax and undefined names
        run: |
          python -m flake8 backend scripts \
            --count \
            --select=E9,F63,F7,F82 \
            --show-source \
            --statistics

      - name: Run pytest
        env:
          SECRET_KEY: ci-test-secret-key
          DEBUG: "false"
          DJANGO_SETTINGS_MODULE: config.settings
          PYTHONPATH: backend
        run: python -m pytest backend -v
YAML

cat > requirements.txt <<'REQ'
# Root dependency entry point used by GitHub Actions and local development.
-r backend/requirements-dev.txt
REQ

cat > backend/requirements-dev.txt <<'REQ'
-r requirements.txt

pytest>=8.3,<10.0
pytest-django>=4.9,<5.0
flake8>=7.1,<8.0
REQ

cat > pytest.ini <<'INI'
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
pythonpath = backend
testpaths = backend
python_files = test_*.py *_tests.py tests.py
addopts = --strict-markers --strict-config
INI

echo "Updated files:"
git status --short -- .github/workflows/python-package.yml requirements.txt backend/requirements-dev.txt pytest.ini

git add .github/workflows/python-package.yml requirements.txt backend/requirements-dev.txt pytest.ini
git diff --cached --check

git commit -m "fix(ci): install Django dependencies before pytest"
git push origin HEAD

echo
echo "Pushed commit: $(git rev-parse HEAD)"
echo "Open GitHub Actions and use the NEW run created by this push."
echo "Do not rerun a job whose checkout SHA is a797706e1f835433708d683911227e548cec88c8."
