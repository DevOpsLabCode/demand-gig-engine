variable "name" {
  type = string
}
variable "kms_key_arn" {
  type = string
}
variable "resource_arns" {
  type = list(string)
}
variable "tags" {
  type = map(string)
  default = {}
}
