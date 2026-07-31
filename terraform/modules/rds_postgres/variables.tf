variable "name" {
  type = string
}
variable "subnet_ids" {
  type = list(string)
}
variable "security_group_ids" {
  type = list(string)
}
variable "kms_key_arn" {
  type = string
}
variable "engine_version" {
  type = string
  default = "17"
}
variable "instance_class" {
  type = string
}
variable "allocated_storage" {
  type = number
}
variable "multi_az" {
  type = bool
}
variable "deletion_protection" {
  type = bool
}
variable "tags" {
  type = map(string)
  default = {}
}

variable "performance_insights_enabled" {
  type        = bool
  description = "Enable RDS Performance Insights on a supported instance class."
  default     = false
}
