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
- **`aws_ses_domain_mail_from.this`:** Creates and manages `aws_ses_domain_mail_from` for this module.
- **`aws_route53_record.mail_from_mx`:** Creates an alias record for the selected AWS endpoint.
- **`aws_route53_record.mail_from_spf`:** Creates an alias record for the selected AWS endpoint.
- **`aws_route53_record.dmarc`:** Creates an alias record for the selected AWS endpoint.
- **Data `data.aws_region.current`:** Reads the provider region for service principals and encryption contexts.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `domain_name` | `string` | `""` | `false` | Verified sending domain. May be empty only when create_dns is false. |
| `hosted_zone_id` | `string` | `""` | `false` | Route 53 public hosted-zone ID that owns domain_name. |
| `create_dns` | `bool` | `false` | `false` | Create the SES identity and all required Route 53 authentication records. |
| `existing_identity_arn` | `string` | `null` | `false` | Optional pre-verified SES domain identity ARN used when DNS and identity lifecycle are managed outside this stack. |
| `mail_from_subdomain` | `string` | `"mail"` | `false` | Subdomain used as the SES custom MAIL FROM domain. |
| `dmarc_policy` | `string` | `"none"` | `false` | DMARC disposition policy. Use quarantine or reject after validating legitimate mail streams. |
| `dmarc_percentage` | `number` | `100` | `false` | Percentage of messages to which the DMARC policy applies. |
| `dmarc_rua` | `string` | `""` | `false` | Optional aggregate-report mailbox without the mailto: prefix. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `identity_arn` | Terraform-created or externally supplied SES domain identity ARN; null only when outbound email is intentionally disabled. | `var.create_dns ? aws_ses_domain_identity.this[0].arn : var.existing_identity_arn` |
| `mail_from_domain` | Custom SES MAIL FROM domain, or null when disabled. | `try(aws_ses_domain_mail_from.this[0].mail_from_domain, null)` |
| `dkim_tokens` | SES Easy DKIM tokens, or an empty list when disabled. | `try(aws_ses_domain_dkim.this[0].dkim_tokens, [])` |

## Security and reliability controls

- Resources use the root stack's encryption, network, logging, tagging, and least-privilege conventions where supported.
- Review plans for public exposure, IAM expansion, encryption changes, replacement, and deletion before applying.

## Example

```hcl
module "ses" {
  source = "./modules/ses"
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
