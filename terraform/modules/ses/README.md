# `ses` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - Domain email identity

Registers the sending domain and creates Route 53 verification and DKIM records.

## What this module does

- **Creates `aws_ses_domain_identity.this`:** Registers the domain identity used to send application email.
- **Creates `aws_route53_record.verification`:** Creates the DNS record used for validation or service routing.
- **Creates `aws_ses_domain_dkim.this`:** Generates DKIM tokens used to authenticate outgoing email.
- **Creates `aws_route53_record.dkim`:** Creates the DNS record used for validation or service routing.

## Execution flow

1. The root stack supplies the inputs listed below.
2. Terraform resolves data sources and derived local values.
3. Resources are created with the inline security and lifecycle controls in `main.tf`.
4. Values in `outputs.tf` are returned to the root stack or deployment scripts.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `domain_name` | `string` | `required` | `false` | Fully qualified DNS name exposed by the service. |
| `hosted_zone_id` | `string` | `required` | `false` | Route 53 hosted-zone ID in which DNS records are created. |
| `create_dns` | `bool` | `required` | `false` | Whether Terraform should create the dns resource or record. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `identity_arn` | ARN of the identity resource consumed by this module. | `try(aws_ses_domain_identity.this[0].arn,null)` |

## Example

```hcl
module "ses" {
  source = "./modules/ses"
  domain_name = var.domain_name
  hosted_zone_id = var.hosted_zone_id
  create_dns = var.create_dns
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
