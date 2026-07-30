#!/usr/bin/env bash
set -euo pipefail

if [[ ! -d .git || ! -f backend/requirements.txt ]]; then
  echo "Run this script from the demand-gig-engine repository root." >&2
  exit 1
fi

mkdir -p .github/workflows

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

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - name: Check out repository
        uses: actions/checkout@v7

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v7
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
          cache-dependency-path: |
            backend/requirements.txt
            requirements.txt

      - name: Install project and test dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements.txt

      - name: Verify Django test environment
        run: |
          python - <<'PY'
          import django
          import pytest
          import pytest_django

          print(f"Django: {django.get_version()}")
          print(f"pytest: {pytest.__version__}")
          print(f"pytest-django: {pytest_django.__version__}")
          PY

      - name: Check Python syntax and undefined names
        run: |
          python -m flake8 backend scripts \
            --count \
            --select=E9,F63,F7,F82 \
            --show-source \
            --statistics

      - name: Check Django configuration
        env:
          DJANGO_SETTINGS_MODULE: config.settings
          PYTHONPATH: backend
        run: |
          python backend/manage.py check
          python backend/manage.py makemigrations --check --dry-run

      - name: Run pytest
        env:
          DJANGO_SETTINGS_MODULE: config.settings
          PYTHONPATH: backend
        run: python -m pytest -q
YAML

cat > requirements.txt <<'REQ'
-r backend/requirements.txt

pytest>=8.4,<10
pytest-django>=4.8,<5
flake8>=7,<8
REQ

cat > pytest.ini <<'INI'
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
pythonpath = backend
testpaths = backend
python_files = test_*.py
addopts = --strict-markers --strict-config
INI

git add .github/workflows/python-package.yml requirements.txt pytest.ini

git commit -m "fix(ci): install Django and configure pytest" || {
  echo "No new changes to commit. Verify that the files are already present."
  exit 0
}

git push origin HEAD:main

echo
echo "Pushed commit: $(git rev-parse HEAD)"
echo "Open GitHub Actions and use the NEW workflow run created by this push."
