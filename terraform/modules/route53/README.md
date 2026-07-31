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
| `enabled` | `bool` | `false` | `false` | Create public alias records. |
| `zone_id` | `string` | `""` | `false` | Route 53 hosted-zone ID that owns record_name. |
| `record_name` | `string` | `""` | `false` | DNS record name created in the hosted zone. |
| `target_name` | `string` | `""` | `false` | AWS alias target DNS name. |
| `target_zone_id` | `string` | `""` | `false` | Canonical hosted-zone ID of the alias target. |
| `create_ipv6` | `bool` | `true` | `false` | Create an AAAA alias in addition to the A alias. |

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
