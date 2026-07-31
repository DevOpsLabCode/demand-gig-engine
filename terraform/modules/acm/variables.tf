variable "domain_name" {
  type = string
  description = "Primary CloudFront viewer domain."
}
variable "subject_alternative_names" {
  type = list(string)
  description = "Additional names, including the private CloudFront-to-ALB origin hostname."
  default = []
}
variable "hosted_zone_id" {
  type = string
  description = "Route 53 hosted zone used for certificate validation."
}
variable "create" {
  type = bool
  default = false
}
variable "tags" {
  type = map(string)
  default = {}
}
