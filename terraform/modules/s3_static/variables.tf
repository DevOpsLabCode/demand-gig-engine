# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the s3 static Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
variable "name" {
  type = string
}

# Input `force_destroy`: Optional customer-managed KMS key. Leave null for SSE-S3, as required by the
# CloudFront static origin design.
# Input `force_destroy`: Whether Terraform may delete the bucket while objects or versions remain.
variable "force_destroy" {
  type    = bool
  default = false
}

# Input `kms_key_arn`: Optional customer-managed KMS key. Leave null for SSE-S3, as required by the CloudFront
# static origin design.
# Input `kms_key_arn`: Optional customer-managed KMS key. Leave null for SSE-S3, as required by the CloudFront static origin design.
variable "kms_key_arn" {
  type        = string
  description = "Optional customer-managed KMS key. Leave null for SSE-S3, as required by the CloudFront static origin design."
  default     = null
}

# Input `create_tls_policy`: Create a standalone TLS-only bucket policy. Disable for buckets whose policy is
# managed by another module.
# Input `create_tls_policy`: Create a standalone TLS-only bucket policy. Disable for buckets whose policy is managed by another module.
variable "create_tls_policy" {
  type        = bool
  description = "Create a standalone TLS-only bucket policy. Disable for buckets whose policy is managed by another module."
  default     = true
}

# Input `noncurrent_version_expiration_days`: Number of days used for noncurrent version expiration retention or timing.
variable "noncurrent_version_expiration_days" {
  type    = number
  default = 30
}

# Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.
variable "tags" {
  type    = map(string)
  default = {}
}
