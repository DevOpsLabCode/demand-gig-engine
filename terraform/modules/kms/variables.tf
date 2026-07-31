# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the kms Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
variable "name" {
  type = string
}
# Input `deletion_window`: Configured KMS recovery window before a scheduled deletion becomes permanent.
variable "deletion_window" {
  type = number
  default = 30
}
# Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.
variable "tags" {
  type = map(string)
  default = {}
}
