# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the encrypted campaign-expiry scheduler, retry, and SQS target contract.

variable "name" {
  type        = string
  description = "Stable Scheduler group, role, and schedule name prefix."

  validation {
    condition     = trimspace(var.name) != "" && length(var.name) <= 64
    error_message = "name must be non-empty and no longer than 64 characters."
  }
}

variable "queue_arn" {
  type        = string
  description = "SQS source queue ARN that receives campaign-expiry scan requests."

  validation {
    condition     = can(regex("^arn:[^:]+:sqs:[^:]+:[0-9]{12}:", var.queue_arn))
    error_message = "queue_arn must be an SQS queue ARN."
  }
}

variable "dlq_arn" {
  type        = string
  description = "SQS dead-letter queue ARN used when Scheduler delivery is exhausted."

  validation {
    condition     = can(regex("^arn:[^:]+:sqs:[^:]+:[0-9]{12}:", var.dlq_arn))
    error_message = "dlq_arn must be an SQS queue ARN."
  }
}

variable "kms_key_arn" {
  type        = string
  description = "Customer-managed KMS key ARN used by Scheduler and the encrypted queues."

  validation {
    condition     = can(regex("^arn:[^:]+:kms:[^:]+:[0-9]{12}:key/", var.kms_key_arn))
    error_message = "kms_key_arn must be a KMS key ARN."
  }
}

variable "schedule_enabled" {
  type        = bool
  description = "Enable or disable the campaign-expiry schedule without deleting it."
  default     = true
}

variable "schedule_expression" {
  type        = string
  description = "AWS Scheduler cron(...) or rate(...) expression."
  default     = "rate(5 minutes)"

  validation {
    condition     = can(regex("^(cron|rate)\\(", var.schedule_expression))
    error_message = "schedule_expression must be an AWS cron(...) or rate(...) expression."
  }
}

variable "maximum_event_age_seconds" {
  type        = number
  description = "Maximum age of an undelivered scheduled event before it is discarded."
  default     = 3600

  validation {
    condition     = floor(var.maximum_event_age_seconds) == var.maximum_event_age_seconds && var.maximum_event_age_seconds >= 60 && var.maximum_event_age_seconds <= 86400
    error_message = "maximum_event_age_seconds must be a whole number between 60 and 86400."
  }
}

variable "maximum_retry_attempts" {
  type        = number
  description = "Scheduler delivery retry attempts before the event is sent to the DLQ."
  default     = 3

  validation {
    condition     = floor(var.maximum_retry_attempts) == var.maximum_retry_attempts && var.maximum_retry_attempts >= 0 && var.maximum_retry_attempts <= 185
    error_message = "maximum_retry_attempts must be a whole number between 0 and 185."
  }
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
