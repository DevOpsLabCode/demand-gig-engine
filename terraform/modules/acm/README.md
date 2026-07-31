# `acm` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - TLS certificate lifecycle

Requests DNS-validated certificates and creates the validation records needed before CloudFront or an ALB can terminate HTTPS.

## What this module does

- **Creates `aws_acm_certificate.this`:** Requests a TLS certificate for encrypted viewer or origin connections.
- **Creates `aws_route53_record.validation`:** Creates the DNS record used for validation or service routing.
- **Creates `aws_acm_certificate_validation.this`:** Waits for DNS validation before dependent services use the certificate.

## Execution flow

1. The root stack supplies the inputs listed below.
2. Terraform resolves data sources and derived local values.
3. Resources are created with the inline security and lifecycle controls in `main.tf`.
4. Values in `outputs.tf` are returned to the root stack or deployment scripts.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `domain_name` | `string` | `required` | `false` | Primary CloudFront viewer domain. |
| `subject_alternative_names` | `list(string)` | `[]` | `false` | Additional names, including the private CloudFront-to-ALB origin hostname. |
| `hosted_zone_id` | `string` | `required` | `false` | Route 53 hosted zone used for certificate validation. |
| `create` | `bool` | `false` | `false` | Whether this module created a certificate rather than reusing an existing ARN. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags applied to supported resources. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `certificate_arn` | ACM certificate ARN used to terminate TLS. | `try(aws_acm_certificate_validation.this[0].certificate_arn,null)` |

## Example

```hcl
module "acm" {
  source = "./modules/acm"
  domain_name = var.domain_name
  hosted_zone_id = var.hosted_zone_id
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
