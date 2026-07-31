# `backup` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - Managed backup policy

Creates an encrypted AWS Backup vault, retention plan, service role, and tag-based resource selection.

## What this module does

- **Creates `aws_iam_role.this`:** Creates an IAM role with a narrowly defined trust relationship.
- **Creates `aws_iam_role_policy_attachment.this`:** Attaches a managed IAM policy required by the role.
- **Creates `aws_backup_vault.this`:** Creates encrypted storage for AWS Backup recovery points.
- **Creates `aws_backup_plan.this`:** Defines backup frequency, retention, and lifecycle policy.
- **Creates `aws_backup_selection.this`:** Selects protected resources through the backup service role and tags.
- **Reads `aws_iam_policy_document.assume`:** Build the trust policy that permits only the AWS Backup service to assume the backup role.

## Execution flow

1. The root stack supplies the inputs listed below.
2. Terraform resolves data sources and derived local values.
3. Resources are created with the inline security and lifecycle controls in `main.tf`.
4. Values in `outputs.tf` are returned to the root stack or deployment scripts.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names, logs, tags, and service identifiers. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key ARN used to encrypt supported data, logs, queues, or secrets. |
| `resource_arns` | `list(string)` | `required` | `false` | Protected resource ARNs selected by the AWS Backup plan. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags applied to supported resources. |

## Outputs

This module does not publish outputs.

## Example

```hcl
module "backup" {
  source = "./modules/backup"
  name = var.name
  kms_key_arn = var.kms_key_arn
  resource_arns = var.resource_arns
}
```

> The root `terraform/main.tf` contains the authoritative production composition. The example above shows the module interface, not a complete standalone deployment.

## Security and reliability notes

- Review every input before production use; defaults are conveniences, not substitutes for environment-specific risk review.
- Keep secret values in AWS Secrets Manager or protected CI/CD secrets. Do not place credentials in `.tfvars` committed to Git.
- Run `terraform fmt`, `terraform validate`, TFLint, Checkov, and the Go contract tests before applying changes.
- Inspect the plan for replacement, deletion, public exposure, IAM expansion, encryption changes, and cross-account effects.

## Files

- `main.tf` - resources and service configuration.
- `variables.tf` - input contract, validation, and defaults.
- `outputs.tf` - values exposed to callers when present.

## Validation

```bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
tflint --recursive
checkov -d .
```

See [`../../README.md`](../../README.md) for environment deployment and [`../../../docs/terraform-module-architecture.md`](../../../docs/terraform-module-architecture.md) for the complete architecture.
