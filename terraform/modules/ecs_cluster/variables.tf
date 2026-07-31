
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the ECS cluster and audit-log contract.

variable "name" { type = string }
variable "kms_key_arn" { type = string }

variable "log_retention_days" {
  type        = number
  description = "ECS Exec log retention; one year is the security baseline."
  default     = 365

  validation {
    condition     = var.log_retention_days >= 365
    error_message = "ECS Exec logs must be retained for at least 365 days."
  }
}

variable "tags" {
  type    = map(string)
  default = {}
}
