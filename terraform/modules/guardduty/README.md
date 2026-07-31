# `guardduty` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - Managed threat detection

Enables Amazon GuardDuty for continuous analysis of supported AWS telemetry.

## What this module does

- **Creates `aws_guardduty_detector.this`:** Enables managed threat detection for the AWS account and region.

## Execution flow

1. The root stack supplies the inputs listed below.
2. Terraform resolves data sources and derived local values.
3. Resources are created with the inline security and lifecycle controls in `main.tf`.
4. Values in `outputs.tf` are returned to the root stack or deployment scripts.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `enabled` | `bool` | `true` | `false` | Whether the optional detector, record, schedule, or resource is enabled. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags applied to supported resources. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `detector_id` | Identifier of the detector resource consumed by this module. | `try(aws_guardduty_detector.this[0].id,null)` |

## Example

```hcl
module "guardduty" {
  source = "./modules/guardduty"
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
