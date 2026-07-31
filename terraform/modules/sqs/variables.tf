
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the SQS Terraform module.

variable "name" {
  type        = string
  description = "Stable queue-name prefix."
}

variable "kms_key_arn" {
  type        = string
  description = "Customer-managed KMS key ARN used by both queues."
}

variable "tags" {
  type        = map(string)
  description = "Common ownership, environment, cost, and governance tags."
  default     = {}
}
