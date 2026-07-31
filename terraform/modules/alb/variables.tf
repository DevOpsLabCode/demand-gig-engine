# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares internet-facing ALB networking, TLS, deletion protection, and access logging inputs.

variable "name" {
  type        = string
  description = "ALB and target-group name prefix."

  validation {
    condition     = can(regex("^[A-Za-z0-9][A-Za-z0-9-]{2,31}$", substr(var.name, 0, min(length(var.name), 32))))
    error_message = "name must contain at least three ALB-compatible characters."
  }
}

variable "vpc_id" {
  type        = string
  description = "VPC ID that owns the target group."

  validation {
    condition     = can(regex("^vpc-[0-9a-f]+$", var.vpc_id))
    error_message = "vpc_id must be a valid VPC ID."
  }
}

variable "subnet_ids" {
  type        = list(string)
  description = "Public subnet IDs spanning at least two Availability Zones."

  validation {
    condition     = length(var.subnet_ids) >= 2 && alltrue([for id in var.subnet_ids : can(regex("^subnet-[0-9a-f]+$", id))])
    error_message = "subnet_ids must contain at least two valid subnet IDs."
  }
}

variable "security_group_ids" {
  type        = list(string)
  description = "Security groups attached to the ALB."

  validation {
    condition     = length(var.security_group_ids) > 0 && alltrue([for id in var.security_group_ids : can(regex("^sg-[0-9a-f]+$", id))])
    error_message = "security_group_ids must contain at least one valid security-group ID."
  }
}

variable "certificate_arn" {
  type        = string
  description = "Regional ACM certificate used by the HTTPS listener; null enables the restricted CloudFront-only HTTP origin path."
  default     = null
  nullable    = true

  validation {
    condition     = var.certificate_arn == null || can(regex("^arn:[^:]+:acm:[^:]+:[0-9]{12}:certificate/", var.certificate_arn))
    error_message = "certificate_arn must be null or an ACM certificate ARN."
  }
}

variable "origin_verify_header_value" {
  type        = string
  description = "High-entropy shared secret injected by CloudFront and required by ALB forwarding rules to prevent direct origin bypass."
  sensitive   = true

  validation {
    condition     = length(var.origin_verify_header_value) >= 32 && can(regex("^[A-Za-z0-9_-]+$", var.origin_verify_header_value))
    error_message = "origin_verify_header_value must contain at least 32 URL/header-safe characters."
  }
}

variable "deletion_protection" {
  type        = bool
  description = "Reject accidental ALB deletion."
  default     = true
}

variable "access_log_bucket_id" {
  type        = string
  description = "Centralized S3 access-log bucket name."

  validation {
    condition     = length(trimspace(var.access_log_bucket_id)) >= 3
    error_message = "access_log_bucket_id must be a non-empty bucket name."
  }
}

variable "access_log_prefix" {
  type        = string
  description = "Relative S3 prefix that must match the log bucket delivery policy."
  default     = "alb"

  validation {
    condition     = trim(var.access_log_prefix, "/") != "" && !startswith(var.access_log_prefix, "/")
    error_message = "access_log_prefix must be a non-empty relative S3 prefix."
  }
}

variable "tags" {
  type        = map(string)
  description = "Common ownership, environment, cost, and governance tags."
  default     = {}
}
