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
- **`aws_secretsmanager_secret.db`:** Creates a KMS-encrypted secret with a recovery window.
- **`aws_secretsmanager_secret_version.db`:** Stores the generated runtime or integration value.
- **`aws_db_subnet_group.this`:** Places database resources in isolated subnets.
- **`aws_db_parameter_group.this`:** Enforces database-engine settings such as PostgreSQL TLS.
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
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names and tags. |
| `subnet_ids` | `list(string)` | `required` | `false` | Subnet IDs that determine resource placement. |
| `security_group_ids` | `list(string)` | `required` | `false` | Security groups attached to the resource. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key ARN used for encryption. |
| `engine_version` | `string` | `"17"` | `false` | Configuration value for `engine_version`. |
| `instance_class` | `string` | `required` | `false` | Configuration value for `instance_class`. |
| `allocated_storage` | `number` | `required` | `false` | Configuration value for `allocated_storage`. |
| `multi_az` | `bool` | `true` | `false` | Maintain a synchronous standby in another Availability Zone. |
| `deletion_protection` | `bool` | `true` | `false` | Reject accidental database deletion. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `endpoint` | Published `endpoint` value. | `aws_db_instance.this.address` |
| `proxy_endpoint` | Published `proxy_endpoint` value. | `aws_db_proxy.this.endpoint` |
| `secret_arn` | Published `secret_arn` value. | `aws_secretsmanager_secret.db.arn` |
| `db_arn` | Published `db_arn` value. | `aws_db_instance.this.arn` |
| `runtime_secret_arn` | Published `runtime_secret_arn` value. | `aws_secretsmanager_secret.runtime.arn` |

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
