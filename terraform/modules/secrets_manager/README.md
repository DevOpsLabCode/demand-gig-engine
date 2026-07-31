# `secrets_manager` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - Provider credential vault

Creates the social, payment, and integration credential secret while allowing safe out-of-band rotation.

## What this module does

- **Creates `aws_secretsmanager_secret.social`:** Creates a protected secret container whose value is consumed at runtime.
- **Creates `aws_secretsmanager_secret_version.initial`:** Initializes or updates the JSON value stored in Secrets Manager.

## Execution flow

1. The root stack supplies the inputs listed below.
2. Terraform resolves data sources and derived local values.
3. Resources are created with the inline security and lifecycle controls in `main.tf`.
4. Values in `outputs.tf` are returned to the root stack or deployment scripts.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names, logs, tags, and service identifiers. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key ARN used to encrypt supported data, logs, queues, or secrets. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags applied to supported resources. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `secret_arn` | ARN of the secret resource consumed by this module. | `aws_secretsmanager_secret.social.arn` |

## Example

```hcl
module "secrets_manager" {
  source = "./modules/secrets_manager"
  name = var.name
  kms_key_arn = var.kms_key_arn
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
