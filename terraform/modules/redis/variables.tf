# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the redis Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
variable "name" {
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
# Input `kms_key_arn`: Customer-managed KMS key ARN used to encrypt supported data, logs, queues, or secrets.
variable "kms_key_arn" {
  type = string
}
# Input `node_type`: ElastiCache node size controlling Redis capacity and performance.
variable "node_type" {
  type = string
}
# Input `replicas`: Configured number of Redis replica nodes.
variable "replicas" {
  type = number
}
# Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.
variable "tags" {
  type = map(string)
  default = {}
}
