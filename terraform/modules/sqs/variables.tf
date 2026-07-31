# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares encrypted work-queue timing, retry, retention, and ownership controls.

variable "name" {
  type        = string
  description = "Stable queue-name prefix."

  validation {
    condition     = can(regex("^[A-Za-z0-9_-]{3,70}$", var.name))
    error_message = "name must contain 3-70 SQS-compatible characters."
  }
}

variable "kms_key_arn" {
  type        = string
  description = "Customer-managed KMS key ARN used by both queues."

  validation {
    condition     = can(regex("^arn:[^:]+:kms:[^:]+:[0-9]{12}:key/", var.kms_key_arn))
    error_message = "kms_key_arn must be a valid KMS key ARN."
  }
}

variable "visibility_timeout_seconds" {
  type        = number
  description = "Time a worker owns a received message before it becomes visible again."
  default     = 300

  validation {
    condition     = floor(var.visibility_timeout_seconds) == var.visibility_timeout_seconds && var.visibility_timeout_seconds >= 30 && var.visibility_timeout_seconds <= 43200
    error_message = "visibility_timeout_seconds must be a whole number between 30 and 43200."
  }
}

variable "message_retention_seconds" {
  type        = number
  description = "Retention period for unprocessed source-queue messages."
  default     = 345600

  validation {
    condition     = floor(var.message_retention_seconds) == var.message_retention_seconds && var.message_retention_seconds >= 60 && var.message_retention_seconds <= 1209600
    error_message = "message_retention_seconds must be a whole number between 60 and 1209600."
  }
}

variable "dlq_retention_seconds" {
  type        = number
  description = "Retention period for failed messages in the dead-letter queue."
  default     = 1209600

  validation {
    condition     = floor(var.dlq_retention_seconds) == var.dlq_retention_seconds && var.dlq_retention_seconds >= var.message_retention_seconds && var.dlq_retention_seconds <= 1209600
    error_message = "dlq_retention_seconds must be at least message_retention_seconds and no more than 1209600."
  }
}

variable "max_receive_count" {
  type        = number
  description = "Number of failed receives before a message is moved to the DLQ."
  default     = 5

  validation {
    condition     = floor(var.max_receive_count) == var.max_receive_count && var.max_receive_count >= 1 && var.max_receive_count <= 1000
    error_message = "max_receive_count must be a whole number between 1 and 1000."
  }
}

variable "receive_wait_time_seconds" {
  type        = number
  description = "Long-poll duration used by workers."
  default     = 20

  validation {
    condition     = floor(var.receive_wait_time_seconds) == var.receive_wait_time_seconds && var.receive_wait_time_seconds >= 0 && var.receive_wait_time_seconds <= 20
    error_message = "receive_wait_time_seconds must be a whole number between 0 and 20."
  }
}

variable "tags" {
  type        = map(string)
  description = "Common ownership, environment, cost, and governance tags."
  default     = {}
}
