#!/usr/bin/env bash
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Runs the complete application, infrastructure, and security validation sequence from one entry point.
# Execution model: fail fast, validate prerequisites, run each documented phase, and surface errors.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

./scripts/run_full_tests.sh
./scripts/security_scan.sh
