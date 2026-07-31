# `alb` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Application ingress and origin TLS

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_lb.this`:** Creates the Application Load Balancer and its security, deletion-protection, and access-log settings.
- **`aws_lb_target_group.backend`:** Registers ECS IP targets and defines application health checks.
- **`aws_lb_listener.http_redirect`:** Defines an HTTP redirect, restricted development origin, or HTTPS listener.
- **`aws_lb_listener.http_cloudfront_origin`:** Defines an HTTP redirect, restricted development origin, or HTTPS listener.
- **`aws_lb_listener.https`:** Defines an HTTP redirect, restricted development origin, or HTTPS listener.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names and tags. |
| `vpc_id` | `string` | `required` | `false` | ID of the VPC that owns the resources. |
| `subnet_ids` | `list(string)` | `required` | `false` | Subnet IDs that determine resource placement. |
| `security_group_ids` | `list(string)` | `required` | `false` | Security groups attached to the resource. |
| `certificate_arn` | `string` | `null` | `false` | ACM certificate ARN used for TLS; null enables the documented restricted development path. |
| `deletion_protection` | `bool` | `true` | `false` | Configuration value for `deletion_protection`. |
| `access_log_bucket_id` | `string` | `required` | `false` | Configuration value for `access_log_bucket_id`. |
| `access_log_prefix` | `string` | `"alb"` | `false` | Configuration value for `access_log_prefix`. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `arn` | Published `arn` value. | `aws_lb.this.arn` |
| `dns_name` | Published `dns_name` value. | `aws_lb.this.dns_name` |
| `zone_id` | Published `zone_id` value. | `aws_lb.this.zone_id` |
| `target_group_arn` | Published `target_group_arn` value. | `aws_lb_target_group.backend.arn` |

## Security and reliability controls

- Deletion protection enabled by default.
- Central S3 access logging.
- HTTPS with TLS 1.2/1.3 policy.
- HTTP redirects to HTTPS when a certificate exists.

## Example

```hcl
module "alb" {
  source = "./modules/alb"
  name = var.name
  vpc_id = var.vpc_id
  subnet_ids = var.subnet_ids
  security_group_ids = var.security_group_ids
  access_log_bucket_id = var.access_log_bucket_id
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
