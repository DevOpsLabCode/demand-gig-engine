# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the alb Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
variable "name" {
  type = string
}
# Input `vpc_id`: ID of the VPC that owns the resource.
variable "vpc_id" {
  type = string
}
# Input `subnet_ids`: Subnet IDs that determine the private or public network placement of the resource.
variable "subnet_ids" {
  type = list(string)
}
# Input `security_group_ids`: Security groups attached to the workload network interface.
variable "security_group_ids" {
  type = list(string)
}
# Input `certificate_arn`: ACM certificate ARN used to terminate TLS.
variable "certificate_arn" {
  type = string
  default = null
}
# Input `deletion_protection`: Whether the managed service rejects accidental deletion.
variable "deletion_protection" {
  type = bool
  default = false
}
# Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.
variable "tags" {
  type = map(string)
  default = {}
}
