# `ecs_cluster` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — ECS cluster and encrypted exec logging

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_ecs_cluster.this`:** Creates the ECS control plane for Fargate services and tasks.
- **`aws_cloudwatch_log_group.exec`:** Stores encrypted logs with a policy-enforced retention period.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names and tags. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key ARN used for encryption. |
| `log_retention_days` | `number` | `365` | `false` | ECS Exec log retention; one year is the security baseline. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `cluster_arn` | Published `cluster_arn` value. | `aws_ecs_cluster.this.arn` |
| `cluster_name` | Published `cluster_name` value. | `aws_ecs_cluster.this.name` |

## Security and reliability controls

- KMS-encrypted ECS Exec logs.
- At least 365 days of log retention.

## Example

```hcl
module "ecs_cluster" {
  source = "./modules/ecs_cluster"
  name = var.name
  kms_key_arn = var.kms_key_arn
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
