# `access_logs` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Centralized access-log storage

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_s3_bucket.this`:** Creates private object storage for application data, state, or audit logs.
- **`aws_s3_bucket_ownership_controls.this`:** Defines bucket ownership and log-delivery ACL behavior.
- **`aws_s3_bucket_acl.this`:** Keeps the log destination private while supporting required delivery ACLs.
- **`aws_s3_bucket_public_access_block.this`:** Blocks public ACL and bucket-policy exposure.
- **`aws_s3_bucket_versioning.this`:** Preserves historical object versions for recovery and investigation.
- **`aws_s3_bucket_server_side_encryption_configuration.this`:** Encrypts new objects at rest.
- **`aws_s3_bucket_lifecycle_configuration.this`:** Aborts failed uploads and controls archival and expiration.
- **`aws_s3_bucket_policy.this`:** Applies service-delivery permissions and denies insecure transport.
- **Data `data.aws_caller_identity.current`:** Reads the active AWS account for account-scoped ARNs and policies.
- **Data `data.aws_partition.current`:** Keeps generated ARNs compatible with the active AWS partition.
- **Data `data.aws_canonical_user_id.current`:** Reads `aws_canonical_user_id` metadata required by this module.
- **Data `data.aws_iam_policy_document.this`:** Builds a structured IAM, resource, trust, or key policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names and tags. |
| `force_destroy` | `bool` | `false` | `false` | Configuration value for `force_destroy`. |
| `alb_prefix` | `string` | `"alb"` | `false` | Configuration value for `alb_prefix`. |
| `retention_days` | `number` | `365` | `false` | Configuration value for `retention_days`. |
| `noncurrent_version_expiration_days` | `number` | `90` | `false` | Configuration value for `noncurrent_version_expiration_days`. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `bucket_id` | S3 bucket name supplied to ALB and source-bucket logging configurations. | `aws_s3_bucket.this.id` |
| `bucket_domain_name` | S3 bucket domain name required by the CloudFront logging configuration. | `aws_s3_bucket.this.bucket_domain_name` |
| `bucket_arn` | ARN of the centralized access-log bucket. | `aws_s3_bucket.this.arn` |

## Security and reliability controls

- Private, versioned terminal log sink.
- TLS-only bucket policy.
- Abandoned multipart-upload cleanup.
- 365-day current-log retention by default.

## Example

```hcl
module "access_logs" {
  source = "./modules/access_logs"
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
