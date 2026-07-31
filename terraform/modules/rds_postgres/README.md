# `rds_postgres` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - PostgreSQL data tier

Creates credentials, secrets, subnet groups, encrypted PostgreSQL, enhanced monitoring, RDS Proxy, and runtime connection settings.

## What this module does

- **Creates `aws_iam_role.monitoring`:** Creates an IAM role with a narrowly defined trust relationship.
- **Creates `aws_iam_role_policy_attachment.monitoring`:** Attaches a managed IAM policy required by the role.
- **Creates `random_password.db`:** Generates a high-entropy value without placing a human-selected password in source control.
- **Creates `random_password.django`:** Generates a high-entropy value without placing a human-selected password in source control.
- **Creates `aws_secretsmanager_secret.db`:** Creates a protected secret container whose value is consumed at runtime.
- **Creates `aws_secretsmanager_secret_version.db`:** Initializes or updates the JSON value stored in Secrets Manager.
- **Creates `aws_db_subnet_group.this`:** Restricts the database to private database subnets across Availability Zones.
- **Creates `aws_db_instance.this`:** Creates the managed PostgreSQL database with encryption, backups, and production safety controls.
- **Creates `aws_iam_role.proxy`:** Creates an IAM role with a narrowly defined trust relationship.
- **Creates `aws_iam_role_policy.proxy`:** Attaches least-privilege inline permissions to the IAM role.
- **Creates `aws_db_proxy.this`:** Pools and manages database connections between ECS tasks and PostgreSQL.
- **Creates `aws_db_proxy_default_target_group.this`:** Defines connection-pool behavior for the database proxy.
- **Creates `aws_db_proxy_target.this`:** Registers the PostgreSQL instance as a target behind the database proxy.
- **Creates `aws_secretsmanager_secret.runtime`:** Creates a protected secret container whose value is consumed at runtime.
- **Creates `aws_secretsmanager_secret_version.runtime`:** Initializes or updates the JSON value stored in Secrets Manager.
- **Reads `aws_iam_policy_document.monitoring_assume`:** Build the trust policy that permits the RDS monitoring service to publish enhanced-monitoring metrics.
- **Reads `aws_iam_policy_document.proxy_assume`:** Build the trust policy that allows the managed RDS Proxy service to assume its Secrets Manager access role.

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
| `engine_version` | `string` | `17` | `false` | Requested major or minor managed-service engine version. |
| `instance_class` | `string` | `required` | `false` | RDS instance size controlling CPU, memory, and network capacity. |
| `allocated_storage` | `number` | `required` | `false` | Initial PostgreSQL storage allocation in GiB. |
| `multi_az` | `bool` | `required` | `false` | Whether RDS maintains a synchronous standby in another Availability Zone. |
| `deletion_protection` | `bool` | `required` | `false` | Whether the managed service rejects accidental deletion. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags applied to supported resources. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `endpoint` | Direct RDS PostgreSQL writer endpoint, excluding the port. | `aws_db_instance.this.address` |
| `proxy_endpoint` | RDS Proxy endpoint used by ECS tasks to pool and protect PostgreSQL connections. | `aws_db_proxy.this.endpoint` |
| `secret_arn` | ARN of the secret resource consumed by this module. | `aws_secretsmanager_secret.db.arn` |
| `db_arn` | ARN of the db resource consumed by this module. | `aws_db_instance.this.arn` |
| `runtime_secret_arn` | ARN of the runtime secret resource consumed by this module. | `aws_secretsmanager_secret.runtime.arn` |

## Example

```hcl
module "rds_postgres" {
  source = "./modules/rds_postgres"
  name = var.name
  subnet_ids = var.subnet_ids
  security_group_ids = var.security_group_ids
  kms_key_arn = var.kms_key_arn
  instance_class = var.instance_class
  allocated_storage = var.allocated_storage
  multi_az = var.multi_az
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
