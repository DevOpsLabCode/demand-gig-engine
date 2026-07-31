# Workflow discovery fix validation

This evidence set verifies the July 31, 2026 fix for the security-remediation validator.

The validator no longer assumes that the Terraform workflow is named
`.github/workflows/terraform.yml`. It resolves an optional
`TERRAFORM_WORKFLOW_PATH`, then conventional names, then discovers a matching
workflow by required Terraform validation and dedicated plan/apply-role markers.

Validation includes both the conventional filename and a simulated rename to
`.github/workflows/infrastructure.yml`, plus workflow parsing, module contracts,
repository static checks, documentation links, `go vet`, and race-enabled Go tests.
