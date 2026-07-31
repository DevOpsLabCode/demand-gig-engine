# `ecs_cluster` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - Container control plane

Creates the ECS cluster and ECS Exec log destination used by Fargate workloads.

## What this module does

- **Creates `aws_ecs_cluster.this`:** Creates the ECS control plane that schedules Fargate tasks.
- **Creates `aws_cloudwatch_log_group.exec`:** Stores application, task, or ECS Exec logs with controlled retention.

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
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags applied to supported resources. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `cluster_arn` | ARN of the ECS cluster that will run this service. | `aws_ecs_cluster.this.arn` |
| `cluster_name` | Name of the ECS cluster used to construct service and autoscaling identifiers. | `aws_ecs_cluster.this.name` |

## Example

```hcl
module "ecs_cluster" {
  source = "./modules/ecs_cluster"
  name = var.name
  kms_key_arn = var.kms_key_arn
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
