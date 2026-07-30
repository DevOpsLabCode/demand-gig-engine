# Security Testing

The repository runs automated security checks in GitHub Actions in addition to the application test and coverage workflow.

## GitHub Actions workflows

### Security tests

`.github/workflows/security.yml` runs on pushes and pull requests to `main`, every Tuesday, and by manual dispatch.

Independent jobs run in parallel:

- **Workflow security validation:** parses every workflow, rejects unapproved action majors, and checks the local shell scripts.
- **Checkov:** creates a full IaC/SARIF report and enforces a blocking baseline for Dockerfiles, GitHub Actions, and committed-secret detection.
- **Bandit:** scans production Python and blocks high-severity findings with medium-or-higher confidence.
- **pip-audit:** resolves `backend/requirements.txt` and blocks known vulnerable Python runtime dependencies.
- **Django deployment check:** runs `manage.py check --deploy --fail-level WARNING` with production security settings.
- **npm audit:** resolves frontend metadata without lifecycle scripts and blocks high or critical production vulnerabilities.
- **Security gate:** provides one aggregate required status check.

Reports are retained as GitHub Actions artifacts for 14 days.

### Checkov policy

The full Checkov scan covers Terraform, CloudFormation, Kubernetes, Helm, Bicep/ARM, Serverless, Dockerfiles, GitHub Actions, OpenAPI, and secrets. It is report-only so the repository receives complete SARIF results even while future infrastructure is being designed.

The blocking Checkov gate covers Dockerfiles, GitHub Actions, and secret scanning. It does not use severity-based filtering because Checkov severity names require a Prisma Cloud API key. Any failure in the blocking scope fails the job. `CKV_GHA_5` and `CKV_GHA_6` remain skipped until the project publishes release artifacts that require Cosign signing and SBOM attestations.

### CodeQL

`.github/workflows/codeql.yml` performs CodeQL analysis for Python and JavaScript/TypeScript. Findings appear under **Security → Code scanning** when code scanning is available for the repository.

### Dependency review

`.github/workflows/dependency-review.yml` runs on pull requests and blocks newly introduced high- or critical-severity runtime dependency vulnerabilities.

### Dependabot

`.github/dependabot.yml` checks Python, npm, Docker, and GitHub Actions dependencies weekly.

## Recommended repository settings

Under **Settings → Code security and analysis**, enable:

- Dependency graph
- Dependabot alerts
- Dependabot security updates
- Secret scanning
- Push protection

Under branch protection or a ruleset for `main`, require:

- `Application tests / Backend / Python 3.12`
- `Application tests / Frontend type-check and build`
- `Security tests / Security gate`
- Both CodeQL language checks
- Dependency review for pull requests

## Local execution

Install and run the same security tools locally:

```bash
./scripts/security_scan.sh
```

The script exits nonzero when workflow validation, the blocking Checkov scan, Bandit, pip-audit, or npm audit fails.
