# Security Testing

The repository includes automated GitHub security checks in addition to the application test and coverage workflow.

## GitHub Actions workflows

### Security tests

`.github/workflows/security.yml` runs on pushes and pull requests to `main`, every Tuesday, and on manual dispatch.

It contains independent jobs for:

- **Checkov:** scans Terraform, CloudFormation, Kubernetes, Helm, Bicep/ARM, Serverless, Dockerfiles, GitHub Actions, OpenAPI documents, and committed secrets. It uploads SARIF and blocks high or critical findings.
- **Bandit:** scans production Python source and blocks high-severity findings with medium-or-higher confidence.
- **pip-audit:** checks Python runtime requirements against published vulnerability advisories.
- **npm audit:** checks production frontend dependencies and blocks high or critical vulnerabilities.
- **Workflow validation:** checks workflow YAML structure, approved action major versions, and shell syntax.
- **Security gate:** provides one aggregate status check that fails when any required security job fails.

Reports are retained as GitHub Actions artifacts for 14 days.

### CodeQL

`.github/workflows/codeql.yml` performs GitHub CodeQL analysis for Python and JavaScript/TypeScript. Findings appear under **Security → Code scanning** when code scanning is available for the repository.

### Dependency review

`.github/workflows/dependency-review.yml` runs on pull requests and blocks newly introduced high- or critical-severity runtime dependency vulnerabilities.

### Dependabot

`.github/dependabot.yml` checks Python, npm, Docker, and GitHub Actions dependencies weekly.

## Recommended GitHub repository settings

Under **Settings → Code security and analysis**, enable:

- Dependency graph
- Dependabot alerts
- Dependabot security updates
- Secret scanning
- Push protection

Under branch protection or rulesets for `main`, require:

- `Application tests / Backend / Python 3.12`
- `Application tests / Frontend type-check and build`
- `Security tests / Security gate`
- Both CodeQL language checks
- Dependency review for pull requests

## Local execution

Install and run all security tools:

```bash
./scripts/security_scan.sh
```

The local script exits nonzero when workflow validation, Checkov, Bandit, pip-audit, or npm audit fails.

## Checkov policy

Checkov reports all findings but makes the GitHub job blocking at `HIGH` severity and above. The two artifact-signing checks `CKV_GHA_5` and `CKV_GHA_6` are temporarily skipped because the project does not yet publish signed release artifacts. Remove those skips when release artifact signing and SBOM attestations are introduced.
