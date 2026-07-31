# `alb` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - Application ingress

Creates the Application Load Balancer, target group, health check, HTTP redirect, and HTTPS listener used as the CloudFront API origin.

## What this module does

- **Creates `aws_lb.this`:** Creates the Application Load Balancer that receives CloudFront origin traffic.
- **Creates `aws_lb_target_group.backend`:** Defines backend health checks and the ECS destination for load-balanced requests.
- **Creates `aws_lb_listener.http`:** Accepts HTTP or HTTPS traffic and forwards or redirects it according to the listener policy.
- **Creates `aws_lb_listener.https`:** Accepts HTTP or HTTPS traffic and forwards or redirects it according to the listener policy.

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
| `subnet_ids` | `list(string)` | `required` | `false` | Subnet IDs that determine the private or public network placement of the resource. |
| `security_group_ids` | `list(string)` | `required` | `false` | Security groups attached to the workload network interface. |
| `certificate_arn` | `string` | `null` | `false` | ACM certificate ARN used to terminate TLS. |
| `deletion_protection` | `bool` | `false` | `false` | Whether the managed service rejects accidental deletion. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags applied to supported resources. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `arn` | ARN of the Application Load Balancer for IAM, monitoring, and cross-module references. | `aws_lb.this.arn` |
| `dns_name` | AWS-generated ALB hostname used by Route 53 and the CloudFront origin. | `aws_lb.this.dns_name` |
| `zone_id` | AWS hosted-zone identifier required by an alias target. | `aws_lb.this.zone_id` |
| `target_group_arn` | Optional ALB target-group ARN used to register this ECS service. | `aws_lb_target_group.backend.arn` |

## Example

```hcl
module "alb" {
  source = "./modules/alb"
  name = var.name
  vpc_id = var.vpc_id
  subnet_ids = var.subnet_ids
  security_group_ids = var.security_group_ids
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
