# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the networking Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
variable "name" {
  type = string
}
# Input `cidr`: IPv4 CIDR block allocated to the VPC.
variable "cidr" {
  type = string
}
# Input `az_count`: Number of Availability Zones across which subnet tiers are created.
variable "az_count" {
  type = number
}
# Input `nat_gateway_per_az`: Whether each application Availability Zone receives its own NAT gateway for resilience.
variable "nat_gateway_per_az" {
  type = bool
  default = false
}
# Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.
variable "tags" {
  type = map(string)
  default = {}
}
