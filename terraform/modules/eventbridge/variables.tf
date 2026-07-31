
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the encrypted scheduler and SQS target contract.

variable "name" { type = string }
variable "queue_arn" { type = string }
variable "dlq_arn" { type = string }
variable "kms_key_arn" { type = string }

variable "schedule_enabled" {
  type    = bool
  default = true
}

variable "schedule_expression" {
  type    = string
  default = "rate(5 minutes)"
}

variable "tags" {
  type    = map(string)
  default = {}
}
