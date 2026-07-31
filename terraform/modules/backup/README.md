# `backup` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Immutable encrypted backups

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_iam_role.this`:** Creates a narrowly trusted service or deployment role.
- **`aws_iam_role_policy_attachment.this`:** Attaches an AWS managed service-role policy.
- **`aws_iam_role_policy.kms`:** Grants resource-scoped permissions required by the role.
- **`aws_backup_vault.this`:** Stores recovery points under a customer-managed KMS key.
- **`aws_backup_vault_lock_configuration.this`:** Makes backup retention immutable after the changeable grace period.
- **`aws_backup_plan.this`:** Defines the backup schedule, cold-storage transition, and retention lifecycle.
- **`aws_backup_selection.this`:** Selects the protected resources for the backup plan.
- **Data `data.aws_iam_policy_document.assume`:** Builds a structured IAM, resource, trust, or key policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name for the backup vault and plan. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key ARN used by the backup vault. |
| `resource_arns` | `list(string)` | `required` | `false` | Protected resource ARNs selected by the AWS Backup plan. |
| `schedule_expression` | `string` | `"cron(0 5 ? * * *)"` | `false` | AWS Backup cron expression for the recurring backup window. |
| `minimum_retention_days` | `number` | `35` | `false` | Normal recovery-point deletion age and, when enabled, Vault Lock minimum retention. |
| `maximum_retention_days` | `number` | `3650` | `false` | Maximum recovery-point retention accepted by Vault Lock. |
| `cold_storage_after_days` | `number` | `null` | `false` | Days before eligible recovery points move to cold storage; null disables transition. |
| `enable_vault_lock` | `bool` | `false` | `false` | Enable Compliance-mode Vault Lock. Recommended for production, but intentionally optional for disposable development stacks. |
| `vault_lock_changeable_for_days` | `number` | `3` | `false` | Grace period before Vault Lock becomes immutable compliance mode. |
| `permissions_boundary_arn` | `string` | `required` | `false` | AWS-managed PowerUserAccess policy ARN used as the permissions boundary for every workload IAM role. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `vault_name` | AWS Backup vault name. | `aws_backup_vault.this.name` |
| `vault_arn` | AWS Backup vault ARN. | `aws_backup_vault.this.arn` |
| `plan_id` | AWS Backup plan ID. | `aws_backup_plan.this.id` |
| `vault_lock_enabled` | Whether Compliance-mode Vault Lock is configured. | `var.enable_vault_lock` |

## Security and reliability controls

- Customer-managed KMS encryption.
- Vault Lock compliance controls.
- 365-day minimum retention.
- KMS grants constrained to AWS resources.

## Example

```hcl
module "backup" {
  source = "./modules/backup"
  name = var.name
  kms_key_arn = var.kms_key_arn
  resource_arns = var.resource_arns
  permissions_boundary_arn = var.permissions_boundary_arn
}
```

> The example shows the module contract only. Use `terraform/main.tf` for the complete dependency graph and production wiring.

## Validation

```bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
tflint --recursive
checkov -d .
python scripts/validate_security_remediation.py
```

See [`../../README.md`](../../README.md), [`../../../docs/terraform-module-architecture.md`](../../../docs/terraform-module-architecture.md), [`../../../docs/TERRAFORM_MODULE_DEEP_AUDIT.md`](../../../docs/TERRAFORM_MODULE_DEEP_AUDIT.md), and [`../../../docs/CHECKOV_REMEDIATION.md`](../../../docs/CHECKOV_REMEDIATION.md).
