
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares WAF scope, request-rate threshold, log retention, and tags.

variable "name" {
  type        = string
  description = "Name prefix for the Web ACL and its encrypted log group."
}

variable "scope" {
  type        = string
  description = "WAF scope. CloudFront requires CLOUDFRONT and an us-east-1 provider."
  default     = "CLOUDFRONT"

  validation {
    condition     = contains(["CLOUDFRONT", "REGIONAL"], var.scope)
    error_message = "scope must be CLOUDFRONT or REGIONAL."
  }
}

variable "rate_limit" {
  type        = number
  description = "Maximum requests per five-minute evaluation window per source IP."
  default     = 2000

  validation {
    condition     = var.rate_limit >= 100
    error_message = "rate_limit must be at least 100."
  }
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch retention for full WAF request logs."
  default     = 365

  validation {
    condition     = var.log_retention_days >= 365
    error_message = "WAF logs must be retained for at least 365 days."
  }
}

variable "tags" {
  type        = map(string)
  description = "Common ownership, environment, cost, and governance tags."
  default     = {}
}
