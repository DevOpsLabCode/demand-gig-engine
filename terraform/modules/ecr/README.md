# `ecr` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Encrypted container-image registries

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_ecr_repository.this`:** Creates an encrypted image repository with immutable tags and scanning.
- **`aws_ecr_lifecycle_policy.this`:** Expires unneeded container images according to retention policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names and tags. |
| `repositories` | `set(string)` | `required` | `false` | Configuration value for `repositories`. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key ARN used for encryption. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `repository_urls` | Published `repository_urls` value. | `{for k,v in aws_ecr_repository.this :k => v.repository_url}` |
| `repository_arns` | Published `repository_arns` value. | `[for v in aws_ecr_repository.this :v.arn]` |

## Security and reliability controls

- Resources use the root stack's encryption, network, logging, tagging, and least-privilege conventions where supported.
- Review plans for public exposure, IAM expansion, encryption changes, replacement, and deletion before applying.

## Example

```hcl
module "ecr" {
  source = "./modules/ecr"
  name = var.name
  repositories = var.repositories
  kms_key_arn = var.kms_key_arn
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
