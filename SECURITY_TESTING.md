# Security testing

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

The repository uses one consolidated GitHub Actions workflow with separate application, infrastructure, dependency, static-analysis, and aggregate security jobs. The jobs are intentionally independent so each failure has a specific owner and artifact.

## Security workflow

The consolidated workflow is `.github/workflows/python-package.yml` and runs on pushes and pull requests to `main`, every Tuesday, and by manual dispatch. `scripts/validate_security_remediation.py` also discovers renamed or consolidated security workflow files, or accepts `SECURITY_WORKFLOW_PATH`, so validation does not depend on one filename.

| Job | Scope | Blocking behavior | Artifact |
|---|---|---|---|
| Workflow security validation | YAML structure, approved action majors, Python compilation, shell syntax, remediation invariants | Any validation failure blocks | Console output |
| Checkov policy scan | Terraform, CloudFormation, Kubernetes, Helm, Bicep, ARM, Serverless, Dockerfile, GitHub Actions, OpenAPI, and secrets | Any unsuppressed policy failure blocks after SARIF upload | `checkov-results` |
| Python dependency audit | Root Python runtime and development dependency graph | Vulnerability or incomplete audit blocks | `pip-audit-results` |
| Bandit Python SAST | `backend/` and `scripts/` production automation | High severity with medium-or-higher confidence blocks | `bandit-results` |
| Django deployment check | `manage.py check --deploy --fail-level WARNING` with production settings | Warning or error blocks | Console output |
| npm dependency audit | Frontend production dependency graph | Resolution failure or high/critical vulnerability blocks | `npm-audit-results`; generated lockfile when needed |
| Security gate | Results of all required jobs | Any non-success result blocks | Console summary |

Artifacts are retained for 14 days.

## Checkov enforcement

The complete Checkov scan is a strict gate. It does not use `--soft-fail`. The step captures Checkov's exit code, uploads SARIF, publishes compatible findings to GitHub Security, and then enforces the original result.

The repository uses inline suppressions only for documented architecture or AWS API constraints. Every suppression must include a specific reason and must be located inside the exact Terraform resource or data block it governs. `scripts/validate_security_remediation.py` checks the controls added for the July 31, 2026 remediation, rejects undocumented exceptions, and rejects out-of-scope suppression placement. See [`docs/CHECKOV_REMEDIATION.md`](docs/CHECKOV_REMEDIATION.md) for the finding-by-finding mapping.

`CKV_GHA_5` and `CKV_GHA_6` remain workflow-wide skips because this project does not currently publish signed release binaries or attestations from this workflow. Container and artifact signing should be added with the release process rather than represented as a control that does not yet exist.

## npm audit behavior

A committed `frontend/package-lock.json` is preferred because it makes `npm ci` and auditing deterministic. Older branches without a lockfile remain scannable:

1. The job warns that the lockfile is missing.
2. It runs `npm install --package-lock-only --ignore-scripts`.
3. It uploads the generated lockfile when resolution succeeds.
4. It runs `npm audit --omit=dev --audit-level=high`.

When npm cannot resolve dependencies, the job writes a valid `npm-audit.json` document with `DEPENDENCY_RESOLUTION_FAILED`, uploads it, and then fails. This prevents the former condition where the job failed before producing diagnostic evidence.

## Other security workflows

- `.github/workflows/codeql.yml` analyzes Python and JavaScript/TypeScript.
- `.github/workflows/dependency-review.yml` blocks high/critical vulnerabilities newly introduced by pull requests.
- `.github/workflows/python-package.yml` runs application tests, linting, type checking, the frontend build, the 90% coverage gate, native Terraform formatting/validation, TFLint, Go race tests, Checkov, plans, and protected deployments.
- `.github/dependabot.yml` checks Python, npm, Docker, Terraform, and GitHub Actions dependencies on its configured cadence.

## Recommended repository rules

Enable the dependency graph, Dependabot alerts/security updates, secret scanning, and push protection. Require these statuses on `main`:

- `Application, security, and Terraform tests / Backend / Python 3.12`
- `Application, security, and Terraform tests / Frontend type-check and build`
- `Application, security, and Terraform tests / Security gate`
- Terraform validation and test gate
- Both CodeQL language analyses
- Dependency review on pull requests

## Local commands

```bash
python scripts/static_checks.py
python scripts/validate_workflows.py
python scripts/validate_security_remediation.py
./scripts/security_scan.sh

cd terraform/tests
go test -race -count=1 ./...
go vet ./...
```

The scanner-backed commands additionally require Python and npm dependencies, Terraform providers, vulnerability databases, and outbound registry access.
