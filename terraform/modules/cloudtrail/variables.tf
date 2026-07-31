# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares encrypted CloudTrail storage, notification, logging, retention, data-event, and Insights inputs.

variable "name" {
  type        = string
  description = "Stable trail, bucket, notification, role, and log-group name prefix."

  validation {
    condition     = can(regex("^[A-Za-z0-9._-]{3,128}$", var.name))
    error_message = "name must contain 3-128 CloudTrail-compatible characters."
  }
}

variable "kms_key_arn" {
  type        = string
  description = "Customer-managed KMS key ARN used for CloudTrail, CloudWatch Logs, S3, and SNS encryption."

  validation {
    condition     = can(regex("^arn:[^:]+:kms:[^:]+:[0-9]{12}:key/", var.kms_key_arn))
    error_message = "kms_key_arn must be a valid KMS key ARN."
  }
}

variable "access_log_bucket_id" {
  type        = string
  description = "Centralized S3 access-log bucket receiving CloudTrail bucket server-access logs."

  validation {
    condition     = length(trimspace(var.access_log_bucket_id)) >= 3
    error_message = "access_log_bucket_id must be a non-empty S3 bucket name."
  }
}

variable "retention_days" {
  type        = number
  description = "Days before current CloudTrail S3 log objects expire."
  default     = 365

  validation {
    condition     = floor(var.retention_days) == var.retention_days && var.retention_days >= 90
    error_message = "retention_days must be a whole number of at least 90 days."
  }
}

variable "s3_data_event_bucket_arns" {
  type        = list(string)
  description = "S3 bucket ARNs for which object-level CloudTrail data events are captured. Empty disables data-event billing."
  default     = []

  validation {
    condition     = alltrue([for arn in var.s3_data_event_bucket_arns : can(regex("^arn:[^:]+:s3:::[^/]+$", arn))])
    error_message = "s3_data_event_bucket_arns must contain only S3 bucket ARNs without object suffixes."
  }
}

variable "enable_insights" {
  type        = bool
  description = "Enable billable CloudTrail API-call-rate and API-error-rate Insights events."
  default     = false
}

variable "permissions_boundary_arn" {
  type        = string
  description = "AWS-managed PowerUserAccess policy ARN used as the permissions boundary for every workload IAM role."

  validation {
    condition     = can(regex("^arn:[^:]+:iam::aws:policy/PowerUserAccess$", var.permissions_boundary_arn))
    error_message = "permissions_boundary_arn must be the partition-correct AWS-managed PowerUserAccess policy ARN."
  }
}

variable "tags" {
  type        = map(string)
  description = "Common ownership, environment, cost, and governance tags."
  default     = {}
}
