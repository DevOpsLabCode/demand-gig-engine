# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares CloudFront origins, aliases, certificate, WAF, access logging, and cost controls.

variable "name" {
  type        = string
  description = "Stable distribution, function, OAC, and policy name prefix."

  validation {
    condition     = length(trimspace(var.name)) >= 3 && length(var.name) <= 64
    error_message = "name must contain 3-64 characters."
  }
}

variable "bucket_id" {
  type        = string
  description = "Private static-site S3 bucket ID whose policy is managed by this module."
}

variable "bucket_arn" {
  type        = string
  description = "Private static-site S3 bucket ARN."

  validation {
    condition     = can(regex("^arn:[^:]+:s3:::[^/]+$", var.bucket_arn))
    error_message = "bucket_arn must be an S3 bucket ARN."
  }
}

variable "bucket_domain_name" {
  type        = string
  description = "Regional S3 hostname used by the private origin."

  validation {
    condition     = length(trimspace(var.bucket_domain_name)) > 0
    error_message = "bucket_domain_name must not be empty."
  }
}

variable "alb_domain_name" {
  type        = string
  description = "ALB origin hostname; custom-domain HTTPS mode requires a matching certificate."

  validation {
    condition     = length(trimspace(var.alb_domain_name)) > 0
    error_message = "alb_domain_name must not be empty."
  }
}

variable "origin_verify_header_value" {
  type        = string
  description = "High-entropy shared secret sent only to the ALB origin and matched by ALB listener rules to prevent direct origin bypass."
  sensitive   = true

  validation {
    condition     = length(var.origin_verify_header_value) >= 32 && can(regex("^[A-Za-z0-9_-]+$", var.origin_verify_header_value))
    error_message = "origin_verify_header_value must contain at least 32 URL/header-safe characters."
  }
}

variable "use_https_origin" {
  type        = bool
  description = "Use TLS from CloudFront to the ALB when a custom origin certificate is available."
  default     = false
}

variable "domain_name" {
  type        = string
  description = "Optional public alias. Empty uses the default CloudFront domain."
  default     = ""
}

variable "certificate_arn" {
  type        = string
  description = "Optional us-east-1 ACM certificate ARN used by the public alias."
  default     = null
  nullable    = true

  validation {
    condition     = var.certificate_arn == null || can(regex("^arn:[^:]+:acm:us-east-1:[0-9]{12}:certificate/", var.certificate_arn))
    error_message = "certificate_arn must be null or an us-east-1 ACM certificate ARN."
  }
}

variable "web_acl_arn" {
  type        = string
  description = "ARN of the CLOUDFRONT-scope WAF web ACL."

  validation {
    condition     = can(regex("^arn:[^:]+:wafv2:us-east-1:[0-9]{12}:global/webacl/", var.web_acl_arn))
    error_message = "web_acl_arn must be a global CloudFront WAFv2 web ACL ARN."
  }
}

variable "access_log_bucket_domain_name" {
  type        = string
  description = "S3 bucket domain used for CloudFront standard access logs."

  validation {
    condition     = length(trimspace(var.access_log_bucket_domain_name)) > 0
    error_message = "access_log_bucket_domain_name must not be empty."
  }
}

variable "price_class" {
  type        = string
  description = "CloudFront edge-location price class."
  default     = "PriceClass_100"

  validation {
    condition     = contains(["PriceClass_100", "PriceClass_200", "PriceClass_All"], var.price_class)
    error_message = "price_class must be PriceClass_100, PriceClass_200, or PriceClass_All."
  }
}

variable "tags" {
  type        = map(string)
  description = "Common ownership, environment, cost, and governance tags."
  default     = {}
}

check "viewer_certificate" {
  assert {
    condition     = (var.domain_name == "") == (var.certificate_arn == null)
    error_message = "domain_name and certificate_arn must either both be configured or both be omitted."
  }
}
