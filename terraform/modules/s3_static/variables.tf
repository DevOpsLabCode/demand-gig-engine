variable "name" {
  type = string
}

variable "force_destroy" {
  type    = bool
  default = false
}

variable "kms_key_arn" {
  type        = string
  description = "Optional customer-managed KMS key. Leave null for SSE-S3, as required by the CloudFront static origin design."
  default     = null
}

variable "create_tls_policy" {
  type        = bool
  description = "Create a standalone TLS-only bucket policy. Disable for buckets whose policy is managed by another module."
  default     = true
}

variable "noncurrent_version_expiration_days" {
  type    = number
  default = 30
}

variable "tags" {
  type    = map(string)
  default = {}
}
