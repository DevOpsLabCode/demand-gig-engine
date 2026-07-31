# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the security Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
variable "name" {
  type = string
}
# Input `vpc_id`: ID of the VPC that owns the resource.
variable "vpc_id" {
  type = string
}
# Input `app_port`: Application TCP port allowed between the ALB and ECS tasks.
variable "app_port" {
  type = number
  default = 8000
}
# Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.
variable "tags" {
  type = map(string)
  default = {}
}
