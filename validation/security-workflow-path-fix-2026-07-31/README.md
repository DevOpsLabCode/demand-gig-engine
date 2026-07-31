# Security workflow path remediation validation

Date: 2026-07-31

## Remediation

- Pinned `TERRAFORM_WORKFLOW_PATH` to `.github/workflows/terraform.yml` in the security workflow.
- Pinned `SECURITY_WORKFLOW_PATH` to `.github/workflows/security.yml` in the security workflow.
- Preserved marker-based fallback discovery for repositories that intentionally rename or consolidate workflows.
- Added `scripts/test_workflow_discovery.py` with six regression scenarios covering conventional filenames, renamed workflows, and explicit environment overrides.
- Added the workflow-discovery regression test to the blocking workflow-validation job.

## Validation results

- Workflow discovery regression tests: 6 scenarios passed.
- Security remediation validator: 156 checks passed.
- GitHub Actions workflow validator: 5 workflows passed.
- Terraform module contracts: 25 modules and 31 root instances passed.
- Documentation links: 169 local links across 55 Markdown files passed.
- Static repository checks: 69 passed.
- Python compilation and shell syntax checks passed.

See `validation.log` for command output.

## Checkov note

The supplied Checkov excerpt reports two failed policies but contains only passed-resource details and does not include either failed check ID or failed resource. No policy was suppressed or weakened without that evidence. The workflow remains fail-closed.
