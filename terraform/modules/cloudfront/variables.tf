
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares CloudFront origin, certificate, WAF, logging, and cost controls.

variable "name" { type = string }
variable "bucket_id" { type = string }
variable "bucket_arn" { type = string }
variable "bucket_domain_name" { type = string }

variable "alb_domain_name" {
  type        = string
  description = "ALB origin hostname; custom-domain HTTPS mode requires a matching certificate."
}

variable "use_https_origin" {
  type        = bool
  description = "Use TLS from CloudFront to the ALB when a custom origin certificate is available."
  default     = false
}

variable "domain_name" {
  type    = string
  default = ""
}

variable "certificate_arn" {
  type    = string
  default = null
}

variable "web_acl_arn" {
  type        = string
  description = "ARN of the CLOUDFRONT-scope WAF web ACL."
}

variable "access_log_bucket_domain_name" {
  type        = string
  description = "S3 bucket domain used for CloudFront standard access logs."
}

variable "price_class" {
  type    = string
  default = "PriceClass_100"
}

variable "tags" {
  type    = map(string)
  default = {}
}
