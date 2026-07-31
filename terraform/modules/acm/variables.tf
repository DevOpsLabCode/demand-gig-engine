# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the acm Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `domain_name`: Primary CloudFront viewer domain.
variable "domain_name" {
  type = string
  description = "Primary CloudFront viewer domain."
}
# Input `subject_alternative_names`: Additional names, including the private CloudFront-to-ALB origin
# hostname.
# Input `subject_alternative_names`: Additional names, including the private CloudFront-to-ALB origin hostname.
variable "subject_alternative_names" {
  type = list(string)
  description = "Additional names, including the private CloudFront-to-ALB origin hostname."
  default = []
}
# Input `hosted_zone_id`: Route 53 hosted zone used for certificate validation.
variable "hosted_zone_id" {
  type = string
  description = "Route 53 hosted zone used for certificate validation."
}
# Input `create`: Whether this module created a certificate rather than reusing an existing ARN.
variable "create" {
  type = bool
  default = false
}
# Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.
variable "tags" {
  type = map(string)
  default = {}
}
