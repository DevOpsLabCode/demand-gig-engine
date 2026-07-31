# `s3_static` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - Private object storage

Creates a private, encrypted, versioned S3 bucket with lifecycle controls and TLS-only access enforcement.

## What this module does

- **Creates `aws_s3_bucket.this`:** Creates an encrypted object-storage bucket for static assets, media, logs, or state.
- **Creates `aws_s3_bucket_ownership_controls.this`:** Makes bucket ownership deterministic and disables legacy ACL ownership ambiguity.
- **Creates `aws_s3_bucket_public_access_block.this`:** Prevents accidental public exposure through S3 ACLs or policies.
- **Creates `aws_s3_bucket_versioning.this`:** Retains prior object versions to support recovery and auditability.
- **Creates `aws_s3_bucket_server_side_encryption_configuration.this`:** Enforces server-side encryption for newly written objects.
- **Creates `aws_s3_bucket_lifecycle_configuration.this`:** Transitions or expires objects according to retention and cost policies.
- **Creates `aws_s3_bucket_policy.tls`:** Applies resource-level access controls and transport requirements to the bucket.
- **Reads `aws_iam_policy_document.tls`:** Build the bucket policy that denies every request made without TLS.

## Execution flow

1. The root stack supplies the inputs listed below.
2. Terraform resolves data sources and derived local values.
3. Resources are created with the inline security and lifecycle controls in `main.tf`.
4. Values in `outputs.tf` are returned to the root stack or deployment scripts.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names, logs, tags, and service identifiers. |
| `force_destroy` | `bool` | `false` | `false` | Whether Terraform may delete the bucket while objects or versions remain. |
| `kms_key_arn` | `string` | `null` | `false` | Optional customer-managed KMS key. Leave null for SSE-S3, as required by the CloudFront static origin design. |
| `create_tls_policy` | `bool` | `true` | `false` | Create a standalone TLS-only bucket policy. Disable for buckets whose policy is managed by another module. |
| `noncurrent_version_expiration_days` | `number` | `30` | `false` | Number of days used for noncurrent version expiration retention or timing. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags applied to supported resources. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `bucket_id` | Identifier of the bucket resource consumed by this module. | `aws_s3_bucket.this.id` |
| `bucket_arn` | ARN of the S3 bucket protected or consumed by the module. | `aws_s3_bucket.this.arn` |
| `regional_domain_name` | Regional S3 hostname used by CloudFront origin configuration. | `aws_s3_bucket.this.bucket_regional_domain_name` |

## Example

```hcl
module "s3_static" {
  source = "./modules/s3_static"
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
