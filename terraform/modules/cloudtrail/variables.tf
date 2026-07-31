
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares encrypted CloudTrail storage, notification, logging, and retention inputs.

variable "name" { type = string }
variable "kms_key_arn" { type = string }
variable "access_log_bucket_id" { type = string }

variable "retention_days" {
  type    = number
  default = 365
}

variable "tags" {
  type    = map(string)
  default = {}
}
