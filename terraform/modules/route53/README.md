# `route53` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - DNS alias routing

Creates optional IPv4 and IPv6 Route 53 alias records for CloudFront or regional AWS endpoints.

## What this module does

- **Creates `aws_route53_record.ipv4`:** Creates the DNS record used for validation or service routing.
- **Creates `aws_route53_record.ipv6`:** Creates the DNS record used for validation or service routing.

## Execution flow

1. The root stack supplies the inputs listed below.
2. Terraform resolves data sources and derived local values.
3. Resources are created with the inline security and lifecycle controls in `main.tf`.
4. Values in `outputs.tf` are returned to the root stack or deployment scripts.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `enabled` | `bool` | `required` | `false` | Whether the optional detector, record, schedule, or resource is enabled. |
| `zone_id` | `string` | `required` | `false` | AWS hosted-zone identifier required by an alias target. |
| `record_name` | `string` | `required` | `false` | Route 53 record name created by the module. |
| `target_name` | `string` | `required` | `false` | AWS alias target name referenced by the DNS record. |
| `target_zone_id` | `string` | `required` | `false` | Identifier of the target zone resource consumed by this module. |
| `create_ipv6` | `bool` | `true` | `false` | Create an AAAA alias. Disable for IPv4-only ALB origins. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `fqdn` | Fully qualified DNS record created by the module, or null when DNS creation is disabled. | `try(aws_route53_record.ipv4[0].fqdn,null)` |

## Example

```hcl
module "route53" {
  source = "./modules/route53"
  enabled = var.enabled
  zone_id = var.zone_id
  record_name = var.record_name
  target_name = var.target_name
  target_zone_id = var.target_zone_id
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
