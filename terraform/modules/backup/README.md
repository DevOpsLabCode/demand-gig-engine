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
| `minimum_retention_days` | `number` | `365` | `false` | Minimum immutable retention and normal deletion point for recovery points. |
| `maximum_retention_days` | `number` | `3650` | `false` | Maximum recovery-point retention accepted by Vault Lock. |
| `cold_storage_after_days` | `number` | `90` | `false` | Days before eligible recovery points transition to cold storage. |
| `vault_lock_changeable_for_days` | `number` | `3` | `false` | Grace period before Vault Lock becomes immutable compliance mode. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| — | This module does not publish outputs. | — |

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

See [`../../README.md`](../../README.md), [`../../../docs/terraform-module-architecture.md`](../../../docs/terraform-module-architecture.md), and [`../../../docs/CHECKOV_REMEDIATION.md`](../../../docs/CHECKOV_REMEDIATION.md).
