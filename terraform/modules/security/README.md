# `security` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - Network security boundaries

Creates CloudFront-restricted ALB ingress and isolated application, database, and Redis security groups.

## What this module does

- **Creates `aws_security_group.alb`:** Creates a stateful network firewall boundary with least-privilege ingress and egress rules.
- **Creates `aws_security_group.app`:** Creates a stateful network firewall boundary with least-privilege ingress and egress rules.
- **Creates `aws_security_group.db`:** Creates a stateful network firewall boundary with least-privilege ingress and egress rules.
- **Creates `aws_security_group.redis`:** Creates a stateful network firewall boundary with least-privilege ingress and egress rules.
- **Reads `aws_ec2_managed_prefix_list.cloudfront`:** Read AWS’s managed CloudFront origin-facing address list for restricted ALB ingress.

## Execution flow

1. The root stack supplies the inputs listed below.
2. Terraform resolves data sources and derived local values.
3. Resources are created with the inline security and lifecycle controls in `main.tf`.
4. Values in `outputs.tf` are returned to the root stack or deployment scripts.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names, logs, tags, and service identifiers. |
| `vpc_id` | `string` | `required` | `false` | ID of the VPC that owns the resource. |
| `app_port` | `number` | `8000` | `false` | Application TCP port allowed between the ALB and ECS tasks. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags applied to supported resources. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `alb_sg_id` | Identifier of the alb sg resource consumed by this module. | `aws_security_group.alb.id` |
| `app_sg_id` | Identifier of the app sg resource consumed by this module. | `aws_security_group.app.id` |
| `db_sg_id` | Identifier of the db sg resource consumed by this module. | `aws_security_group.db.id` |
| `redis_sg_id` | Identifier of the redis sg resource consumed by this module. | `aws_security_group.redis.id` |

## Example

```hcl
module "security" {
  source = "./modules/security"
  name = var.name
  vpc_id = var.vpc_id
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
