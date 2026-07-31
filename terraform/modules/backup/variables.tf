
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares backup targets, encryption, immutable-retention, and lifecycle settings.

variable "name" {
  type        = string
  description = "Stable name for the backup vault and plan."
}

variable "kms_key_arn" {
  type        = string
  description = "Customer-managed KMS key ARN used by the backup vault."
}

variable "resource_arns" {
  type        = list(string)
  description = "Protected resource ARNs selected by the AWS Backup plan."
}

variable "minimum_retention_days" {
  type        = number
  description = "Minimum immutable retention and normal deletion point for recovery points."
  default     = 365

  validation {
    condition     = var.minimum_retention_days >= 365
    error_message = "minimum_retention_days must be at least 365."
  }
}

variable "maximum_retention_days" {
  type        = number
  description = "Maximum recovery-point retention accepted by Vault Lock."
  default     = 3650

  validation {
    condition     = var.maximum_retention_days >= var.minimum_retention_days
    error_message = "maximum_retention_days must be greater than or equal to minimum_retention_days."
  }
}

variable "cold_storage_after_days" {
  type        = number
  description = "Days before eligible recovery points transition to cold storage."
  default     = 90

  validation {
    condition     = var.cold_storage_after_days >= 0 && var.cold_storage_after_days + 90 <= var.minimum_retention_days
    error_message = "Cold-stored backups must remain retained for at least 90 additional days."
  }
}

variable "vault_lock_changeable_for_days" {
  type        = number
  description = "Grace period before Vault Lock becomes immutable compliance mode."
  default     = 3

  validation {
    condition     = var.vault_lock_changeable_for_days >= 3
    error_message = "AWS Backup Vault Lock requires at least a three-day changeable period."
  }
}

variable "tags" {
  type        = map(string)
  description = "Common ownership, environment, cost, and governance tags."
  default     = {}
}
