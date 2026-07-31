# `redis` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - Redis cache and coordination

Creates the private subnet group and encrypted, failover-capable ElastiCache replication group.

## What this module does

- **Creates `aws_elasticache_subnet_group.this`:** Restricts Redis nodes to private database subnets.
- **Creates `aws_elasticache_replication_group.this`:** Creates encrypted Redis primary and replica nodes with failover support.

## Execution flow

1. The root stack supplies the inputs listed below.
2. Terraform resolves data sources and derived local values.
3. Resources are created with the inline security and lifecycle controls in `main.tf`.
4. Values in `outputs.tf` are returned to the root stack or deployment scripts.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names, logs, tags, and service identifiers. |
| `subnet_ids` | `list(string)` | `required` | `false` | Subnet IDs that determine the private or public network placement of the resource. |
| `security_group_ids` | `list(string)` | `required` | `false` | Security groups attached to the workload network interface. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key ARN used to encrypt supported data, logs, queues, or secrets. |
| `node_type` | `string` | `required` | `false` | ElastiCache node size controlling Redis capacity and performance. |
| `replicas` | `number` | `required` | `false` | Configured number of Redis replica nodes. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags applied to supported resources. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `endpoint` | Primary Redis endpoint used by the application cache configuration. | `aws_elasticache_replication_group.this.primary_endpoint_address` |
| `port` | Redis listener port exposed by the replication group. | `aws_elasticache_replication_group.this.port` |

## Example

```hcl
module "redis" {
  source = "./modules/redis"
  name = var.name
  subnet_ids = var.subnet_ids
  security_group_ids = var.security_group_ids
  kms_key_arn = var.kms_key_arn
  node_type = var.node_type
  replicas = var.replicas
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
