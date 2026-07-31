
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares resilient PostgreSQL capacity, encryption, and deletion controls.

variable "name" { type = string }
variable "subnet_ids" { type = list(string) }
variable "security_group_ids" { type = list(string) }
variable "kms_key_arn" { type = string }

variable "engine_version" {
  type    = string
  default = "17"
}

variable "instance_class" { type = string }
variable "allocated_storage" { type = number }

variable "multi_az" {
  type        = bool
  description = "Maintain a synchronous standby in another Availability Zone."
  default     = true
}

variable "deletion_protection" {
  type        = bool
  description = "Reject accidental database deletion."
  default     = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
