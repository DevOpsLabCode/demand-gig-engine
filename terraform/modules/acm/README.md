# `acm` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — TLS certificate provisioning

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_acm_certificate.this`:** Requests a DNS-validated ACM certificate.
- **`aws_route53_record.validation`:** Creates an alias record for the selected AWS endpoint.
- **`aws_acm_certificate_validation.this`:** Waits for successful ACM DNS validation.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `domain_name` | `string` | `""` | `false` | Primary certificate name. Empty is permitted only when certificate creation is disabled. |
| `subject_alternative_names` | `list(string)` | `[]` | `false` | Additional certificate names. |
| `hosted_zone_id` | `string` | `""` | `false` | Route 53 hosted zone used for DNS validation. |
| `create` | `bool` | `false` | `false` | Create and DNS-validate a certificate in this module. |
| `existing_certificate_arn` | `string` | `null` | `false` | Existing ACM certificate ARN used when create is false; null leaves TLS certificate selection to the caller. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `certificate_arn` | Created and validated ACM certificate ARN, supplied existing ARN, or null when TLS is intentionally not configured. | `var.create ? aws_acm_certificate_validation.this[0].certificate_arn : var.existing_certificate_arn` |

## Security and reliability controls

- Resources use the root stack's encryption, network, logging, tagging, and least-privilege conventions where supported.
- Review plans for public exposure, IAM expansion, encryption changes, replacement, and deletion before applying.

## Example

```hcl
module "acm" {
  source = "./modules/acm"
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
