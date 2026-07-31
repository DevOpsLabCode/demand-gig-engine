# `xray` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Distributed tracing resources

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_xray_sampling_rule.this`:** Creates and manages `aws_xray_sampling_rule` for this module.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names and tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| — | This module does not publish outputs. | — |

## Security and reliability controls

- Resources use the root stack's encryption, network, logging, tagging, and least-privilege conventions where supported.
- Review plans for public exposure, IAM expansion, encryption changes, replacement, and deletion before applying.

## Example

```hcl
module "xray" {
  source = "./modules/xray"
  name = var.name
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
