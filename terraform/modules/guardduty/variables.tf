# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the guardduty Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `enabled`: Whether the optional detector, record, schedule, or resource is enabled.
variable "enabled" {
  type = bool
  default = true
}
# Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.
variable "tags" {
  type = map(string)
  default = {}
}
