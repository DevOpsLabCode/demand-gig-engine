# `cloudtrail` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Account activity audit trail

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_s3_bucket.logs`:** Creates private object storage for application data, state, or audit logs.
- **`aws_s3_bucket_ownership_controls.logs`:** Defines bucket ownership and log-delivery ACL behavior.
- **`aws_s3_bucket_public_access_block.logs`:** Blocks public ACL and bucket-policy exposure.
- **`aws_s3_bucket_versioning.logs`:** Preserves historical object versions for recovery and investigation.
- **`aws_s3_bucket_server_side_encryption_configuration.logs`:** Encrypts new objects at rest.
- **`aws_s3_bucket_logging.logs`:** Delivers source-bucket access records to the central log sink.
- **`aws_s3_bucket_lifecycle_configuration.logs`:** Aborts failed uploads and controls archival and expiration.
- **`aws_s3_bucket_policy.logs`:** Applies service-delivery permissions and denies insecure transport.
- **`aws_sns_topic.notifications`:** Creates an encrypted notification or alarm topic.
- **`aws_sns_topic_policy.notifications`:** Restricts SNS administration, publication, and transport security.
- **`aws_cloudwatch_log_group.trail`:** Stores encrypted logs with a policy-enforced retention period.
- **`aws_iam_role.cloudtrail_logs`:** Creates a narrowly trusted service or deployment role.
- **`aws_iam_role_policy.cloudtrail_logs`:** Grants resource-scoped permissions required by the role.
- **`aws_cloudtrail.this`:** Records validated multi-region AWS API activity.
- **Data `data.aws_caller_identity.current`:** Reads the active AWS account for account-scoped ARNs and policies.
- **Data `data.aws_partition.current`:** Keeps generated ARNs compatible with the active AWS partition.
- **Data `data.aws_region.current`:** Reads the provider region for service principals and encryption contexts.
- **Data `data.aws_iam_policy_document.logs`:** Builds a structured IAM, resource, trust, or key policy.
- **Data `data.aws_iam_policy_document.notifications`:** Builds a structured IAM, resource, trust, or key policy.
- **Data `data.aws_iam_policy_document.cloudtrail_logs_assume`:** Builds a structured IAM, resource, trust, or key policy.
- **Data `data.aws_iam_policy_document.cloudtrail_logs`:** Builds a structured IAM, resource, trust, or key policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable trail, bucket, notification, role, and log-group name prefix. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key ARN used for CloudTrail, CloudWatch Logs, S3, and SNS encryption. |
| `access_log_bucket_id` | `string` | `required` | `false` | Centralized S3 access-log bucket receiving CloudTrail bucket server-access logs. |
| `retention_days` | `number` | `365` | `false` | Days before current CloudTrail S3 log objects expire. |
| `s3_data_event_bucket_arns` | `list(string)` | `[]` | `false` | S3 bucket ARNs for which object-level CloudTrail data events are captured. Empty disables data-event billing. |
| `enable_insights` | `bool` | `false` | `false` | Enable billable CloudTrail API-call-rate and API-error-rate Insights events. |
| `permissions_boundary_arn` | `string` | `required` | `false` | AWS-managed PowerUserAccess policy ARN used as the permissions boundary for every workload IAM role. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `trail_arn` | ARN of the multi-region CloudTrail trail. | `aws_cloudtrail.this.arn` |
| `log_bucket_arn` | ARN of the encrypted CloudTrail S3 log bucket. | `aws_s3_bucket.logs.arn` |
| `notification_topic_arn` | ARN of the encrypted CloudTrail SNS notification topic. | `aws_sns_topic.notifications.arn` |
| `cloudwatch_log_group_arn` | ARN of the encrypted CloudTrail CloudWatch log group. | `aws_cloudwatch_log_group.trail.arn` |

## Security and reliability controls

- Multi-region validated trail.
- KMS encryption.
- Encrypted SNS delivery notifications.
- Versioned private S3 archive.

## Example

```hcl
module "cloudtrail" {
  source = "./modules/cloudtrail"
  name = var.name
  kms_key_arn = var.kms_key_arn
  access_log_bucket_id = var.access_log_bucket_id
  permissions_boundary_arn = var.permissions_boundary_arn
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
