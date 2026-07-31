# `kms` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Customer-managed application encryption key

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_kms_key.this`:** Creates a rotating customer-managed encryption key with a constrained key policy.
- **`aws_kms_alias.this`:** Publishes a stable human-readable alias for the KMS key.
- **Data `data.aws_caller_identity.current`:** Reads the active AWS account for account-scoped ARNs and policies.
- **Data `data.aws_region.current`:** Reads the provider region for service principals and encryption contexts.
- **Data `data.aws_partition.current`:** Keeps generated ARNs compatible with the active AWS partition.
- **Data `data.aws_iam_policy_document.this`:** Builds a structured IAM, resource, trust, or key policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names and tags. |
| `deletion_window` | `number` | `30` | `false` | Configuration value for `deletion_window`. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `key_arn` | Published `key_arn` value. | `aws_kms_key.this.arn` |
| `key_id` | Published `key_id` value. | `aws_kms_key.this.key_id` |

## Security and reliability controls

- Annual key rotation.
- 30-day deletion window by default.
- Service principals constrained by account, source ARN, or encryption context.

## Example

```hcl
module "kms" {
  source = "./modules/kms"
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
