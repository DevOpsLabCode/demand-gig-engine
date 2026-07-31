variable "name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_group_ids" {
  type = list(string)
}

variable "certificate_arn" {
  type    = string
  default = null
}

variable "origin_verify_header_name" {
  type        = string
  description = "Private header CloudFront must send before the ALB forwards traffic."
}

variable "origin_verify_header_value" {
  type        = string
  sensitive   = true
  description = "Random private value CloudFront must send before the ALB forwards traffic."
}

variable "deletion_protection" {
  type    = bool
  default = false
}

variable "tags" {
  type    = map(string)
  default = {}
}
