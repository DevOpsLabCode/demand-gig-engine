variable "name" {
  type = string
}
variable "bucket_id" {
  type = string
}
variable "bucket_arn" {
  type = string
}
variable "bucket_domain_name" {
  type = string
}
variable "alb_domain_name" {
  type = string
  description = "Origin hostname used by CloudFront. For HTTPS this must be covered by the ALB certificate."
}
variable "use_https_origin" {
  type = bool
  description = "Use TLS between CloudFront and the ALB."
  default = false
}
variable "domain_name" {
  type = string
  default = ""
}
variable "certificate_arn" {
  type = string
  default = null
}
variable "web_acl_arn" {
  type = string
  description = "ARN of the CLOUDFRONT-scope WAF web ACL."
}
variable "price_class" {
  type = string
  default = "PriceClass_100"
}
variable "tags" {
  type = map(string)
  default = {}
}

variable "origin_verify_header_name" {
  type        = string
  description = "Private header name CloudFront sends to the ALB."
}

variable "origin_verify_header_value" {
  type        = string
  sensitive   = true
  description = "Private header value CloudFront sends to the ALB."
}
