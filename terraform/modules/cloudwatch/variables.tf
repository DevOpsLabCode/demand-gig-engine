
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares encrypted operational-alert inputs.

variable "name" { type = string }
variable "alb_arn_suffix" { type = string }
variable "cluster_name" { type = string }
variable "service_name" { type = string }

variable "sns_email" {
  type    = string
  default = ""
}

variable "kms_key_arn" {
  type        = string
  description = "Customer-managed KMS key used to encrypt the alarm SNS topic."
}

variable "account_root_arn" {
  type        = string
  description = "Owning account root ARN used by the explicit SNS administration policy."
}

variable "tags" {
  type    = map(string)
  default = {}
}
