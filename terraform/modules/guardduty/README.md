# `guardduty` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Managed threat detection

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_guardduty_detector.this`:** Enables managed AWS threat detection.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `enabled` | `bool` | `true` | `false` | Configuration value for `enabled`. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `detector_id` | Published `detector_id` value. | `try(aws_guardduty_detector.this[0].id,null)` |

## Security and reliability controls

- Resources use the root stack's encryption, network, logging, tagging, and least-privilege conventions where supported.
- Review plans for public exposure, IAM expansion, encryption changes, replacement, and deletion before applying.

## Example

```hcl
module "guardduty" {
  source = "./modules/guardduty"
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
