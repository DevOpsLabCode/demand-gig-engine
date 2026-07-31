# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares authenticated Redis capacity, placement, encryption, backup, and availability controls.

variable "name" {
  type        = string
  description = "Stable replication-group and secret name prefix."

  validation {
    condition     = length(trimspace(var.name)) >= 3 && length(var.name) <= 40
    error_message = "name must contain 3-40 characters so derived ElastiCache identifiers remain valid."
  }
}

variable "subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs used by the ElastiCache subnet group."

  validation {
    condition     = length(var.subnet_ids) >= 2 && alltrue([for id in var.subnet_ids : can(regex("^subnet-[0-9a-f]+$", id))])
    error_message = "subnet_ids must contain at least two valid subnet IDs."
  }
}

variable "security_group_ids" {
  type        = list(string)
  description = "Security groups attached to the replication group."

  validation {
    condition     = length(var.security_group_ids) > 0 && alltrue([for id in var.security_group_ids : can(regex("^sg-[0-9a-f]+$", id))])
    error_message = "security_group_ids must contain at least one valid security-group ID."
  }
}

variable "kms_key_arn" {
  type        = string
  description = "Customer-managed KMS key ARN used for data and secret encryption."

  validation {
    condition     = can(regex("^arn:[^:]+:kms:[^:]+:[0-9]{12}:key/", var.kms_key_arn))
    error_message = "kms_key_arn must be a KMS key ARN, not an alias ARN."
  }
}

variable "engine_version" {
  type        = string
  description = "Redis-compatible ElastiCache engine version."
  default     = "7.1"

  validation {
    condition     = can(regex("^[0-9]+(\\.[0-9]+)?$", var.engine_version))
    error_message = "engine_version must use a numeric major or major.minor value."
  }
}

variable "node_type" {
  type        = string
  description = "ElastiCache node type controlling memory, network, and CPU capacity."

  validation {
    condition     = can(regex("^cache\\.[a-z0-9]+\\.[a-z0-9]+$", var.node_type))
    error_message = "node_type must be an ElastiCache node class such as cache.t4g.micro."
  }
}

variable "replicas" {
  type        = number
  description = "Number of read replicas. Zero is permitted for cost-limited development; production is enforced at the root module."

  validation {
    condition     = floor(var.replicas) == var.replicas && var.replicas >= 0 && var.replicas <= 5
    error_message = "replicas must be a whole number between 0 and 5."
  }
}

variable "snapshot_retention_days" {
  type        = number
  description = "Number of days ElastiCache retains automatic snapshots."
  default     = 7

  validation {
    condition     = floor(var.snapshot_retention_days) == var.snapshot_retention_days && var.snapshot_retention_days >= 1 && var.snapshot_retention_days <= 35
    error_message = "snapshot_retention_days must be a whole number between 1 and 35."
  }
}


variable "log_retention_days" {
  type        = number
  description = "CloudWatch retention for Redis engine and slow-query logs."
  default     = 365

  validation {
    condition     = floor(var.log_retention_days) == var.log_retention_days && var.log_retention_days >= 365
    error_message = "log_retention_days must be a whole number of at least 365."
  }
}

variable "apply_immediately" {
  type        = bool
  description = "Apply service changes immediately rather than during the maintenance window. Keep false for production."
  default     = false
}

variable "tags" {
  type        = map(string)
  description = "Common ownership, environment, cost, and governance tags."
  default     = {}
}
