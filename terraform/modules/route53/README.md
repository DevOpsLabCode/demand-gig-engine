# `route53` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — DNS aliases for CloudFront and ALB

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_route53_record.ipv4`:** Creates an alias record for the selected AWS endpoint.
- **`aws_route53_record.ipv6`:** Creates an alias record for the selected AWS endpoint.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `enabled` | `bool` | `required` | `false` | Configuration value for `enabled`. |
| `zone_id` | `string` | `required` | `false` | Configuration value for `zone_id`. |
| `record_name` | `string` | `required` | `false` | Configuration value for `record_name`. |
| `target_name` | `string` | `required` | `false` | Configuration value for `target_name`. |
| `target_zone_id` | `string` | `required` | `false` | Configuration value for `target_zone_id`. |
| `create_ipv6` | `bool` | `true` | `false` | Create an AAAA alias. Disable for IPv4-only ALB origins. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `fqdn` | Published `fqdn` value. | `try(aws_route53_record.ipv4[0].fqdn,null)` |

## Security and reliability controls

- Resources use the root stack's encryption, network, logging, tagging, and least-privilege conventions where supported.
- Review plans for public exposure, IAM expansion, encryption changes, replacement, and deletion before applying.

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
