variable "enabled" {
  type = bool
}
variable "zone_id" {
  type = string
}
variable "record_name" {
  type = string
}
variable "target_name" {
  type = string
}
variable "target_zone_id" {
  type = string
}

variable "create_ipv6" {
  type        = bool
  description = "Create an AAAA alias. Disable for IPv4-only ALB origins."
  default     = true
}
