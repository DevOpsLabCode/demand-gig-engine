# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the rds postgres Terraform module.
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
# Input `engine_version`: Requested major or minor managed-service engine version.
variable "engine_version" {
  type = string
  default = "17"
}
# Input `instance_class`: RDS instance size controlling CPU, memory, and network capacity.
variable "instance_class" {
  type = string
}
# Input `allocated_storage`: Initial PostgreSQL storage allocation in GiB.
variable "allocated_storage" {
  type = number
}
# Input `multi_az`: Whether RDS maintains a synchronous standby in another Availability Zone.
variable "multi_az" {
  type = bool
}
# Input `deletion_protection`: Whether the managed service rejects accidental deletion.
variable "deletion_protection" {
  type = bool
}
# Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.
variable "tags" {
  type = map(string)
  default = {}
}
