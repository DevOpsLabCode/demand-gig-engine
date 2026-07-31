# `redis` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Authenticated encrypted Redis

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_elasticache_subnet_group.this`:** Places Redis nodes in isolated database subnets.
- **`random_password.auth`:** Generates a strong credential without storing plaintext in source control.
- **`aws_elasticache_replication_group.this`:** Creates encrypted authenticated Redis with optional Multi-AZ failover.
- **`aws_secretsmanager_secret.runtime`:** Creates a KMS-encrypted secret with a recovery window.
- **`aws_secretsmanager_secret_version.runtime`:** Stores the generated runtime or integration value.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names and tags. |
| `subnet_ids` | `list(string)` | `required` | `false` | Subnet IDs that determine resource placement. |
| `security_group_ids` | `list(string)` | `required` | `false` | Security groups attached to the resource. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key ARN used for encryption. |
| `node_type` | `string` | `required` | `false` | Configuration value for `node_type`. |
| `replicas` | `number` | `required` | `false` | Number of Redis replicas. Production resilience requires at least one replica. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `endpoint` | Primary Redis endpoint; applications should normally consume runtime_secret_arn instead. | `aws_elasticache_replication_group.this.primary_endpoint_address` |
| `port` | TLS Redis listener port. | `aws_elasticache_replication_group.this.port` |
| `runtime_secret_arn` | Secrets Manager ARN containing the authenticated REDIS_URL value. | `aws_secretsmanager_secret.runtime.arn` |

## Security and reliability controls

- At-rest and in-transit encryption.
- Generated authentication token.
- Multi-AZ automatic failover with at least one required replica.
- Authenticated TLS URL stored in Secrets Manager.

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
