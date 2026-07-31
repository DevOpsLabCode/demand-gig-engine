
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares private application-bucket encryption, logging, and lifecycle controls.

variable "name" { type = string }

variable "force_destroy" {
  type    = bool
  default = false
}

variable "kms_key_arn" {
  type        = string
  description = "Optional customer-managed key; null selects SSE-S3 for CloudFront compatibility."
  default     = null
}

variable "create_tls_policy" {
  type        = bool
  description = "Create the TLS-only bucket policy unless another module owns the complete policy."
  default     = true
}

variable "access_log_bucket_id" {
  type        = string
  description = "Central log bucket that receives server access records."
}

variable "noncurrent_version_expiration_days" {
  type    = number
  default = 30
}

variable "tags" {
  type    = map(string)
  default = {}
}
