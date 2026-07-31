# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the cloudfront Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
variable "name" {
  type = string
}
# Input `bucket_id`: Origin hostname used by CloudFront. For HTTPS this must be covered by the ALB
# certificate.
# Input `bucket_id`: Identifier of the bucket resource consumed by this module.
variable "bucket_id" {
  type = string
}
# Input `bucket_arn`: Origin hostname used by CloudFront. For HTTPS this must be covered by the ALB
# certificate.
# Input `bucket_arn`: ARN of the S3 bucket protected or consumed by the module.
variable "bucket_arn" {
  type = string
}
# Input `bucket_domain_name`: Origin hostname used by CloudFront. For HTTPS this must be covered by the ALB
# certificate.
# Input `bucket_domain_name`: Regional bucket hostname passed to CloudFront as its private origin.
variable "bucket_domain_name" {
  type = string
}
# Input `alb_domain_name`: Origin hostname used by CloudFront. For HTTPS this must be covered by the ALB
# certificate.
# Input `alb_domain_name`: Origin hostname used by CloudFront. For HTTPS this must be covered by the ALB certificate.
variable "alb_domain_name" {
  type = string
  description = "Origin hostname used by CloudFront. For HTTPS this must be covered by the ALB certificate."
}
# Input `use_https_origin`: Use TLS between CloudFront and the ALB.
variable "use_https_origin" {
  type = bool
  description = "Use TLS between CloudFront and the ALB."
  default = false
}
# Input `domain_name`: Fully qualified DNS name exposed by the service.
variable "domain_name" {
  type = string
  default = ""
}
# Input `certificate_arn`: ACM certificate ARN used to terminate TLS.
variable "certificate_arn" {
  type = string
  default = null
}
# Input `web_acl_arn`: ARN of the CLOUDFRONT-scope WAF web ACL.
variable "web_acl_arn" {
  type = string
  description = "ARN of the CLOUDFRONT-scope WAF web ACL."
}
# Input `price_class`: CloudFront edge-location price class used to balance reach and cost.
variable "price_class" {
  type = string
  default = "PriceClass_100"
}
# Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.
variable "tags" {
  type = map(string)
  default = {}
}
