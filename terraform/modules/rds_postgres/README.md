# `rds_postgres` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Resilient encrypted PostgreSQL and RDS Proxy

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_iam_role.monitoring`:** Creates a narrowly trusted service or deployment role.
- **`aws_iam_role_policy_attachment.monitoring`:** Attaches an AWS managed service-role policy.
- **`random_password.db`:** Generates a strong credential without storing plaintext in source control.
- **`random_password.django`:** Generates a strong credential without storing plaintext in source control.
- **`random_id.final_snapshot`:** Creates and manages `random_id` for this module.
- **`aws_secretsmanager_secret.db`:** Creates a KMS-encrypted secret with a recovery window.
- **`aws_secretsmanager_secret_version.db`:** Stores the generated runtime or integration value.
- **`aws_db_subnet_group.this`:** Places database resources in isolated subnets.
- **`aws_db_parameter_group.this`:** Enforces database-engine settings such as PostgreSQL TLS.
- **`aws_cloudwatch_log_group.postgresql`:** Stores encrypted logs with a policy-enforced retention period.
- **`aws_cloudwatch_log_group.upgrade`:** Stores encrypted logs with a policy-enforced retention period.
- **`aws_db_instance.this`:** Creates encrypted Multi-AZ PostgreSQL with backups and deletion protection.
- **`aws_iam_role.proxy`:** Creates a narrowly trusted service or deployment role.
- **`aws_iam_role_policy.proxy`:** Grants resource-scoped permissions required by the role.
- **`aws_db_proxy.this`:** Provides pooled TLS database connections using a protected secret.
- **`aws_db_proxy_default_target_group.this`:** Defines RDS Proxy connection-pool behavior.
- **`aws_db_proxy_target.this`:** Registers PostgreSQL as the RDS Proxy target.
- **`aws_secretsmanager_secret.runtime`:** Creates a KMS-encrypted secret with a recovery window.
- **`aws_secretsmanager_secret_version.runtime`:** Stores the generated runtime or integration value.
- **Data `data.aws_iam_policy_document.monitoring_assume`:** Builds a structured IAM, resource, trust, or key policy.
- **Data `data.aws_iam_policy_document.proxy_assume`:** Builds a structured IAM, resource, trust, or key policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable identifier for the database, proxy, subnet group, roles, and secrets. |
| `subnet_ids` | `list(string)` | `required` | `false` | Private database subnet IDs spanning at least two Availability Zones. |
| `security_group_ids` | `list(string)` | `required` | `false` | Security groups attached to the RDS instance and proxy. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key ARN used by RDS, Performance Insights, and Secrets Manager. |
| `engine_version` | `string` | `"17"` | `false` | PostgreSQL engine major or major.minor version. |
| `instance_class` | `string` | `required` | `false` | RDS instance class. |
| `allocated_storage` | `number` | `required` | `false` | Initial gp3 storage allocation in GiB. |
| `max_allocated_storage` | `number` | `null` | `false` | Maximum autoscaled storage in GiB; null uses five times the initial allocation. |
| `multi_az` | `bool` | `true` | `false` | Maintain a synchronous standby in another Availability Zone. |
| `backup_retention_days` | `number` | `30` | `false` | Number of days automated backups and point-in-time recovery are retained. |
| `performance_insights_retention_days` | `number` | `731` | `false` | Performance Insights retention. AWS accepts 7 or 731 days for this configuration. |
| `log_retention_days` | `number` | `365` | `false` | CloudWatch retention for PostgreSQL and upgrade logs exported by RDS. |
| `monitoring_interval_seconds` | `number` | `60` | `false` | Enhanced Monitoring interval in seconds. |
| `deletion_protection` | `bool` | `true` | `false` | Reject accidental database deletion. |
| `apply_immediately` | `bool` | `false` | `false` | Apply changes immediately instead of waiting for the maintenance window. Keep false for production. |
| `secret_recovery_window_days` | `number` | `30` | `false` | Secrets Manager deletion recovery window for database and runtime secrets. |
| `permissions_boundary_arn` | `string` | `required` | `false` | AWS-managed PowerUserAccess policy ARN used as the permissions boundary for every workload IAM role. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `endpoint` | Direct RDS PostgreSQL writer endpoint, excluding the port. | `aws_db_instance.this.address` |
| `proxy_endpoint` | RDS Proxy endpoint used by ECS tasks to pool and protect PostgreSQL connections. | `aws_db_proxy.this.endpoint` |
| `secret_arn` | Secrets Manager ARN containing the database login used by RDS Proxy. | `aws_secretsmanager_secret.db.arn` |
| `db_arn` | RDS database instance ARN used by AWS Backup. | `aws_db_instance.this.arn` |
| `db_identifier` | RDS identifier used by CloudWatch alarm dimensions. | `aws_db_instance.this.identifier` |
| `runtime_secret_arn` | Secrets Manager ARN containing DATABASE_URL and the Django SECRET_KEY. | `aws_secretsmanager_secret.runtime.arn` |

## Security and reliability controls

- Multi-AZ and deletion protection enabled by default.
- KMS encryption and enforced TLS.
- 30-day backups and 731-day Performance Insights.
- RDS Proxy with protected credentials.

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
