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
variable "node_type" {
  type = string
}
variable "replicas" {
  type = number
}
variable "tags" {
  type = map(string)
  default = {}
}
