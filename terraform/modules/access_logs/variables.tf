
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the centralized access-log bucket contract.

# Stable globally unique bucket name used by all delivery integrations.
variable "name" {
  type = string
}

# Permit deletion of non-empty development buckets while production remains protected by default.
variable "force_destroy" {
  type    = bool
  default = false
}

# Prefix used by the ALB access-log block and matching bucket policy.
variable "alb_prefix" {
  type    = string
  default = "alb"
}

# Number of days retained current log objects remain available.
variable "retention_days" {
  type    = number
  default = 365
}

# Number of days retained historical object versions remain available.
variable "noncurrent_version_expiration_days" {
  type    = number
  default = 90
}

# Common ownership, environment, cost, and governance tags.
variable "tags" {
  type    = map(string)
  default = {}
}
