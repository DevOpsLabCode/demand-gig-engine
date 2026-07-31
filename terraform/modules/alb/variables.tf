
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the ALB Terraform module.

variable "name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_group_ids" {
  type = list(string)
}

# ACM certificate used by the HTTPS listener. Null is supported only for the restricted no-domain development path.
variable "certificate_arn" {
  type    = string
  default = null
}

# Production-safe default prevents accidental ALB deletion.
variable "deletion_protection" {
  type    = bool
  default = true
}

# Central log-bucket name configured in the ALB access_logs block.
variable "access_log_bucket_id" {
  type = string
}

# Prefix matched by the centralized log-bucket delivery policy.
variable "access_log_prefix" {
  type    = string
  default = "alb"
}

variable "tags" {
  type    = map(string)
  default = {}
}
