# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the route53 Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `enabled`: Whether the optional detector, record, schedule, or resource is enabled.
variable "enabled" {
  type = bool
}
# Input `zone_id`: AWS hosted-zone identifier required by an alias target.
variable "zone_id" {
  type = string
}
# Input `record_name`: Route 53 record name created by the module.
variable "record_name" {
  type = string
}
# Input `target_name`: AWS alias target name referenced by the DNS record.
variable "target_name" {
  type = string
}
# Input `target_zone_id`: Identifier of the target zone resource consumed by this module.
variable "target_zone_id" {
  type = string
}

# Input `create_ipv6`: Create an AAAA alias. Disable for IPv4-only ALB origins.
variable "create_ipv6" {
  type        = bool
  description = "Create an AAAA alias. Disable for IPv4-only ALB origins."
  default     = true
}
