# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the cloudtrail Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
variable "name" {
  type = string
}
# Input `kms_key_arn`: Customer-managed KMS key ARN used to encrypt supported data, logs, queues, or secrets.
variable "kms_key_arn" {
  type = string
}
# Input `retention_days`: Number of days the protected data, logs, or recovery points are retained.
variable "retention_days" {
  type = number
  default = 365
}
# Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.
variable "tags" {
  type = map(string)
  default = {}
}
