# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the waf Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `name`: Name prefix for the web ACL.
variable "name" {
  type = string
  description = "Name prefix for the web ACL."
}
# Input `scope`: WAF scope. CloudFront requires CLOUDFRONT and an us-east-1 provider.
variable "scope" {
  type = string
  description = "WAF scope. CloudFront requires CLOUDFRONT and an us-east-1 provider."
  default = "CLOUDFRONT"
  validation {
    condition = contains(["CLOUDFRONT","REGIONAL"],var.scope)
    error_message = "scope must be CLOUDFRONT or REGIONAL."
  }
}
# Input `rate_limit`: Maximum requests per five-minute evaluation window per source IP.
variable "rate_limit" {
  type = number
  description = "Maximum requests per five-minute evaluation window per source IP."
  default = 2000
  validation {
    condition = var.rate_limit >= 100
    error_message = "rate_limit must be at least 100."
  }
}
# Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.
variable "tags" {
  type = map(string)
  default = {}
}
