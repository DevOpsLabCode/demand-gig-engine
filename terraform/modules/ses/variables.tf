# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the ses Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `domain_name`: Fully qualified DNS name exposed by the service.
variable "domain_name" {
  type = string
}
# Input `hosted_zone_id`: Route 53 hosted-zone ID in which DNS records are created.
variable "hosted_zone_id" {
  type = string
}
# Input `create_dns`: Whether Terraform should create the dns resource or record.
variable "create_dns" {
  type = bool
}
