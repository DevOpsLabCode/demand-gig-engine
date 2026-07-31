# `cloudtrail` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - Account audit logging

Stores encrypted, versioned CloudTrail logs in a protected S3 bucket and records management activity for investigation and governance.

## What this module does

- **Creates `aws_s3_bucket.logs`:** Creates an encrypted object-storage bucket for static assets, media, logs, or state.
- **Creates `aws_s3_bucket_ownership_controls.logs`:** Makes bucket ownership deterministic and disables legacy ACL ownership ambiguity.
- **Creates `aws_s3_bucket_public_access_block.logs`:** Prevents accidental public exposure through S3 ACLs or policies.
- **Creates `aws_s3_bucket_versioning.logs`:** Retains prior object versions to support recovery and auditability.
- **Creates `aws_s3_bucket_server_side_encryption_configuration.logs`:** Enforces server-side encryption for newly written objects.
- **Creates `aws_s3_bucket_lifecycle_configuration.logs`:** Transitions or expires objects according to retention and cost policies.
- **Creates `aws_s3_bucket_policy.logs`:** Applies resource-level access controls and transport requirements to the bucket.
- **Creates `aws_cloudtrail.this`:** Records AWS API activity for audit, investigation, and governance.
- **Reads `aws_caller_identity.current`:** Read the active AWS account identity for policies, names, and ownership checks.
- **Reads `aws_partition.current`:** Read the AWS partition so service principals and ARNs work in commercial, GovCloud, or China partitions.
- **Reads `aws_region.current`:** Read the current region for KMS encryption-context restrictions and trail configuration.
- **Reads `aws_iam_policy_document.logs`:** Build the S3 bucket policy that permits CloudTrail delivery while denying insecure transport.

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
| `retention_days` | `number` | `365` | `false` | Number of days the protected data, logs, or recovery points are retained. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags applied to supported resources. |

## Outputs

This module does not publish outputs.

## Example

```hcl
module "cloudtrail" {
  source = "./modules/cloudtrail"
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
