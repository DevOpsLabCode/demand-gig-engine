# `kms` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - Customer-managed encryption

Creates the KMS key, policy, rotation configuration, and alias used by data services and logs.

## What this module does

- **Creates `aws_kms_key.this`:** Creates the customer-managed encryption key shared by protected services.
- **Creates `aws_kms_alias.this`:** Provides a stable, human-readable name for the KMS key.
- **Reads `aws_iam_policy_document.this`:** Build the KMS key policy that preserves account administration and grants only required AWS services cryptographic access.

## Execution flow

1. The root stack supplies the inputs listed below.
2. Terraform resolves data sources and derived local values.
3. Resources are created with the inline security and lifecycle controls in `main.tf`.
4. Values in `outputs.tf` are returned to the root stack or deployment scripts.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names, logs, tags, and service identifiers. |
| `deletion_window` | `number` | `30` | `false` | Configured KMS recovery window before a scheduled deletion becomes permanent. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags applied to supported resources. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `key_arn` | ARN of the key resource consumed by this module. | `aws_kms_key.this.arn` |
| `key_id` | Identifier of the key resource consumed by this module. | `aws_kms_key.this.key_id` |

## Example

```hcl
module "kms" {
  source = "./modules/kms"
  name = var.name
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
