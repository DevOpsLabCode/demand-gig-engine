variable "name" {
  type = string
  description = "Name prefix for the web ACL."
}
variable "scope" {
  type = string
  description = "WAF scope. CloudFront requires CLOUDFRONT and an us-east-1 provider."
  default = "CLOUDFRONT"
  validation {
    condition = contains(["CLOUDFRONT","REGIONAL"],var.scope)
    error_message = "scope must be CLOUDFRONT or REGIONAL."
  }
}
variable "rate_limit" {
  type = number
  description = "Maximum requests per five-minute evaluation window per source IP."
  default = 2000
  validation {
    condition = var.rate_limit >= 100
    error_message = "rate_limit must be at least 100."
  }
}
variable "tags" {
  type = map(string)
  default = {}
}
