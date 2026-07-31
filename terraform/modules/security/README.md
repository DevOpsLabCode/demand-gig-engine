# `security` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Least-privilege network security groups

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_security_group.alb`:** Creates a stateful least-privilege network boundary.
- **`aws_security_group.app`:** Creates a stateful least-privilege network boundary.
- **`aws_security_group.db`:** Creates a stateful least-privilege network boundary.
- **`aws_security_group.redis`:** Creates a stateful least-privilege network boundary.
- **Data `data.aws_ec2_managed_prefix_list.cloudfront`:** Reads AWS-managed service network ranges for restricted ingress.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for security-group names and tags. |
| `vpc_id` | `string` | `required` | `false` | ID of the VPC that owns every security group. |
| `vpc_cidr` | `string` | `required` | `false` | Private VPC CIDR used to constrain east-west egress rules. |
| `app_port` | `number` | `8000` | `false` | Application TCP port allowed between the ALB and ECS tasks. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `alb_sg_id` | Published `alb_sg_id` value. | `aws_security_group.alb.id` |
| `app_sg_id` | Published `app_sg_id` value. | `aws_security_group.app.id` |
| `db_sg_id` | Published `db_sg_id` value. | `aws_security_group.db.id` |
| `redis_sg_id` | Published `redis_sg_id` value. | `aws_security_group.redis.id` |

## Security and reliability controls

- CloudFront-only ALB ingress.
- ALB-to-application port restriction.
- Database and Redis ingress only from application tasks.
- No all-protocol internet egress.

## Example

```hcl
module "security" {
  source = "./modules/security"
  name = var.name
  vpc_id = var.vpc_id
  vpc_cidr = var.vpc_cidr
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
