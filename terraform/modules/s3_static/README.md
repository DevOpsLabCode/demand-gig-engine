# `s3_static` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Private versioned object storage

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_s3_bucket.this`:** Creates private object storage for application data, state, or audit logs.
- **`aws_s3_bucket_ownership_controls.this`:** Defines bucket ownership and log-delivery ACL behavior.
- **`aws_s3_bucket_public_access_block.this`:** Blocks public ACL and bucket-policy exposure.
- **`aws_s3_bucket_versioning.this`:** Preserves historical object versions for recovery and investigation.
- **`aws_s3_bucket_server_side_encryption_configuration.this`:** Encrypts new objects at rest.
- **`aws_s3_bucket_logging.this`:** Delivers source-bucket access records to the central log sink.
- **`aws_s3_bucket_lifecycle_configuration.this`:** Aborts failed uploads and controls archival and expiration.
- **`aws_s3_bucket_policy.tls`:** Applies service-delivery permissions and denies insecure transport.
- **Data `data.aws_iam_policy_document.tls`:** Builds a structured IAM, resource, trust, or key policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Globally unique private S3 bucket name. |
| `force_destroy` | `bool` | `false` | `false` | Allow deletion of non-empty disposable development buckets. |
| `kms_key_arn` | `string` | `null` | `false` | Optional customer-managed KMS key; null selects SSE-S3 for CloudFront log-delivery compatibility. |
| `create_tls_policy` | `bool` | `true` | `false` | Create the TLS-only bucket policy unless another module owns the complete bucket policy. |
| `access_log_bucket_id` | `string` | `required` | `false` | Centralized log bucket that receives S3 server-access records. |
| `noncurrent_version_expiration_days` | `number` | `30` | `false` | Days retained superseded object versions before lifecycle expiration. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `bucket_id` | Published `bucket_id` value. | `aws_s3_bucket.this.id` |
| `bucket_arn` | Published `bucket_arn` value. | `aws_s3_bucket.this.arn` |
| `regional_domain_name` | Published `regional_domain_name` value. | `aws_s3_bucket.this.bucket_regional_domain_name` |

## Security and reliability controls

- Resources use the root stack's encryption, network, logging, tagging, and least-privilege conventions where supported.
- Review plans for public exposure, IAM expansion, encryption changes, replacement, and deletion before applying.

## Example

```hcl
module "s3_static" {
  source = "./modules/s3_static"
  name = var.name
  access_log_bucket_id = var.access_log_bucket_id
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
