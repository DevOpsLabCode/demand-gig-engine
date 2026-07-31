# `ses` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Verified transactional-email identity

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_ses_domain_identity.this`:** Registers a domain identity for outbound mail.
- **`aws_route53_record.verification`:** Creates an alias record for the selected AWS endpoint.
- **`aws_ses_domain_dkim.this`:** Creates DKIM tokens for authenticated email.
- **`aws_route53_record.dkim`:** Creates an alias record for the selected AWS endpoint.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `domain_name` | `string` | `required` | `false` | Configuration value for `domain_name`. |
| `hosted_zone_id` | `string` | `required` | `false` | Configuration value for `hosted_zone_id`. |
| `create_dns` | `bool` | `required` | `false` | Configuration value for `create_dns`. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `identity_arn` | Published `identity_arn` value. | `try(aws_ses_domain_identity.this[0].arn,null)` |

## Security and reliability controls

- Resources use the root stack's encryption, network, logging, tagging, and least-privilege conventions where supported.
- Review plans for public exposure, IAM expansion, encryption changes, replacement, and deletion before applying.

## Example

```hcl
module "ses" {
  source = "./modules/ses"
  domain_name = var.domain_name
  hosted_zone_id = var.hosted_zone_id
  create_dns = var.create_dns
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
