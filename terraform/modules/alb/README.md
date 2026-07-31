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
- **`aws_lb_listener_rule.http_cloudfront_origin`:** Creates and manages `aws_lb_listener_rule` for this module.
- **`aws_lb_listener.https`:** Defines an HTTP redirect, restricted development origin, or HTTPS listener.
- **`aws_lb_listener_rule.https_cloudfront_origin`:** Creates and manages `aws_lb_listener_rule` for this module.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | ALB and target-group name prefix. |
| `vpc_id` | `string` | `required` | `false` | VPC ID that owns the target group. |
| `subnet_ids` | `list(string)` | `required` | `false` | Public subnet IDs spanning at least two Availability Zones. |
| `security_group_ids` | `list(string)` | `required` | `false` | Security groups attached to the ALB. |
| `certificate_arn` | `string` | `null` | `false` | Regional ACM certificate used by the HTTPS listener; null enables the restricted CloudFront-only HTTP origin path. |
| `origin_verify_header_value` | `string` | `required` | `true` | High-entropy shared secret injected by CloudFront and required by ALB forwarding rules to prevent direct origin bypass. |
| `deletion_protection` | `bool` | `true` | `false` | Reject accidental ALB deletion. |
| `access_log_bucket_id` | `string` | `required` | `false` | Centralized S3 access-log bucket name. |
| `access_log_prefix` | `string` | `"alb"` | `false` | Relative S3 prefix that must match the log bucket delivery policy. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `arn` | Published `arn` value. | `aws_lb.this.arn` |
| `dns_name` | Published `dns_name` value. | `aws_lb.this.dns_name` |
| `zone_id` | Published `zone_id` value. | `aws_lb.this.zone_id` |
| `target_group_arn` | Published `target_group_arn` value. | `aws_lb_target_group.backend.arn` |
| `target_group_arn_suffix` | Target-group ARN suffix used by CloudWatch dimensions. | `aws_lb_target_group.backend.arn_suffix` |

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
  origin_verify_header_value = var.origin_verify_header_value
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

See [`../../README.md`](../../README.md), [`../../../docs/terraform-module-architecture.md`](../../../docs/terraform-module-architecture.md), [`../../../docs/TERRAFORM_MODULE_DEEP_AUDIT.md`](../../../docs/TERRAFORM_MODULE_DEEP_AUDIT.md), and [`../../../docs/CHECKOV_REMEDIATION.md`](../../../docs/CHECKOV_REMEDIATION.md).
