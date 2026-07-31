# Consolidated workflow remediation

This remediation addresses the GitHub Actions failure:

> No Terraform workflow found. Set TERRAFORM_WORKFLOW_PATH or add a workflow containing bootstrap/account validation and the dedicated plan/apply roles.

## Root cause

The branch executing in GitHub contained `.github/workflows/python-package.yml`, but the validator expected a separate Terraform workflow. The previously packaged repository contained `security.yml` and `terraform.yml`, but those hidden workflow files were not present in the branch that produced the failure.

## Fix

- Consolidated application, security, Checkov, Terraform validation, Terraform plan, and Terraform deployment jobs into `.github/workflows/python-package.yml`.
- Set both `TERRAFORM_WORKFLOW_PATH` and `SECURITY_WORKFLOW_PATH` to the consolidated workflow.
- Removed the runtime dependency on separate `security.yml` and `terraform.yml` files.
- Updated Terraform Go tests to discover governed workflows by required security markers rather than hard-coded filenames.
- Kept dedicated `AWS_TERRAFORM_PLAN_ROLE_ARN` and `AWS_TERRAFORM_APPLY_ROLE_ARN` OIDC roles and the fail-closed Checkov gate.

## Verified

- Workflow YAML validation: 3 files
- Workflow discovery regression tests: 6 scenarios
- Security remediation validator: 156 checks passed
- Terraform contracts: 25 modules and 31 root instances
- Static repository checks: 69 passed
- Documentation links: 169 validated
- Terraform Go race tests: passed
- Python compilation and shell syntax: passed

The backend pytest command was not executed successfully in this offline sandbox because Django and django-allauth are not installed. The GitHub workflow installs project requirements before running pytest.
