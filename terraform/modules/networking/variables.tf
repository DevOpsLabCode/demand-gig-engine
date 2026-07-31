
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares VPC addressing, availability, encryption, and logging controls.

variable "name" { type = string }
variable "cidr" { type = string }
variable "az_count" { type = number }

variable "nat_gateway_per_az" {
  type    = bool
  default = false
}

variable "kms_key_arn" {
  type        = string
  description = "Customer-managed KMS key used by the VPC flow-log group."
}

variable "flow_log_retention_days" {
  type    = number
  default = 365

  validation {
    condition     = var.flow_log_retention_days >= 365
    error_message = "VPC flow logs must be retained for at least 365 days."
  }
}

variable "tags" {
  type    = map(string)
  default = {}
}
