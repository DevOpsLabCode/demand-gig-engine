# `guardduty` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Managed threat detection

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- This module does not directly create Terraform resources.
- **Data `data.aws_guardduty_detector.this`:** Reads `aws_guardduty_detector` metadata required by this module.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `enabled` | `bool` | `true` | `false` | Require an enabled regional GuardDuty detector owned by terraform/global/account. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `detector_id` | ID of the account/region GuardDuty detector, or null when disabled. | `try(data.aws_guardduty_detector.this[0].id, null)` |

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

See [`../../README.md`](../../README.md), [`../../../docs/terraform-module-architecture.md`](../../../docs/terraform-module-architecture.md), [`../../../docs/TERRAFORM_MODULE_DEEP_AUDIT.md`](../../../docs/TERRAFORM_MODULE_DEEP_AUDIT.md), and [`../../../docs/CHECKOV_REMEDIATION.md`](../../../docs/CHECKOV_REMEDIATION.md).
