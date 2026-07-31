# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares private application-bucket encryption, access logging, version retention, and policy ownership.

variable "name" {
  type        = string
  description = "Globally unique private S3 bucket name."

  validation {
    condition     = length(var.name) >= 3 && length(var.name) <= 63 && can(regex("^[a-z0-9][a-z0-9.-]*[a-z0-9]$", var.name))
    error_message = "name must be a valid 3-63 character lowercase S3 bucket name."
  }
}

variable "force_destroy" {
  type        = bool
  description = "Allow deletion of non-empty disposable development buckets."
  default     = false
}

variable "kms_key_arn" {
  type        = string
  description = "Optional customer-managed KMS key; null selects SSE-S3 for CloudFront log-delivery compatibility."
  default     = null
  nullable    = true

  validation {
    condition     = var.kms_key_arn == null || can(regex("^arn:[^:]+:kms:[^:]+:[0-9]{12}:key/", var.kms_key_arn))
    error_message = "kms_key_arn must be null or a valid KMS key ARN."
  }
}

variable "create_tls_policy" {
  type        = bool
  description = "Create the TLS-only bucket policy unless another module owns the complete bucket policy."
  default     = true
}

variable "access_log_bucket_id" {
  type        = string
  description = "Centralized log bucket that receives S3 server-access records."

  validation {
    condition     = length(trimspace(var.access_log_bucket_id)) >= 3
    error_message = "access_log_bucket_id must be a non-empty bucket name."
  }
}

variable "noncurrent_version_expiration_days" {
  type        = number
  description = "Days retained superseded object versions before lifecycle expiration."
  default     = 30

  validation {
    condition     = floor(var.noncurrent_version_expiration_days) == var.noncurrent_version_expiration_days && var.noncurrent_version_expiration_days >= 30
    error_message = "noncurrent_version_expiration_days must be a whole number of at least 30."
  }
}

variable "tags" {
  type        = map(string)
  description = "Common ownership, environment, cost, and governance tags."
  default     = {}
}
