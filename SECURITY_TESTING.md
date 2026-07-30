# Security Testing

The repository uses layered security checks because no single scanner covers application code, dependencies, secrets, workflows, containers, and infrastructure configuration.

## GitHub Actions controls

| Control | Purpose | Enforcement |
|---|---|---|
| CodeQL | Semantic analysis of Python and JavaScript/TypeScript | GitHub code-scanning alerts |
| Checkov | Dockerfile, GitHub Actions, IaC, and secret-policy checks | High and critical findings fail CI; SARIF upload is best-effort |
| Bandit | Python security-pattern analysis | Runs in an independent job; high severity with medium-or-higher confidence fails CI |
| pip-audit | Python dependency CVEs | Runs in an independent job; any confirmed vulnerability fails CI |
| npm audit | Frontend production dependency CVEs | High and critical findings fail CI |
| Dependency Review | Prevents vulnerable runtime dependencies in pull requests | High and critical additions fail PR checks |
| Dependabot | Updates Python, npm, Docker, and GitHub Actions dependencies | Weekly pull requests |

Checkov runs directly from the Python package rather than a third-party container action. This reduces the number of external GitHub Actions that receive workflow execution privileges. Each scanner runs in a separate job, so a dependency-audit failure does not prevent Bandit, Checkov, or npm audit from producing their own results.

`CKV_GHA_5` and `CKV_GHA_6` are excluded because this repository uploads test and scanner reports, not executable release artifacts. Production release artifacts should be signed and attested before delivery.

## Local execution

```bash
./scripts/security_scan.sh
```

The local command requires Python, pip, Node.js, and npm. It runs every scanner and returns a failing exit status only after all scanner exit codes have been reported.

## Required GitHub repository settings

Workflow files cannot enable these settings by themselves. In **Settings → Security and analysis**, enable:

1. Dependency graph
2. Dependabot alerts
3. Dependabot security updates
4. Secret scanning
5. Push protection
6. Code scanning, when it is not already activated by the included CodeQL workflow

Protect `main` and require these checks before merging:

- Backend / Python 3.10
- Backend / Python 3.11
- Backend / Python 3.12
- Frontend type-check and build
- Validate GitHub workflows and scripts
- Checkov policy scan
- Python dependency audit
- Python Bandit SAST
- npm dependency audit
- CodeQL (python)
- CodeQL (javascript-typescript)
- Dependency review

Require pull requests, conversation resolution, and at least one approving review. Two approvals and CODEOWNERS review are preferred for production changes.

## Recommended next stage

Add Trivy or Grype image scanning after production Docker images are built. Checkov validates configuration; it does not replace operating-system and container-package CVE scanning.


## GitHub Actions compatibility

The workflows use the current Node 24-compatible major releases of the official GitHub actions: checkout v7, setup-python v7, setup-node v7, upload-artifact v7, dependency-review-action v5, and CodeQL v4. Checkout credentials are not persisted.

`scripts/validate_workflows.py` checks all workflow YAML files, required workflow keys, job timeouts, and the approved action major versions. The security workflow runs this validation before the scanners. SARIF publication is marked best-effort so a repository without code-scanning entitlement can still enforce the Checkov command result and retain the SARIF artifact.
