variable "name" {
  type = string
}
variable "alb_arn_suffix" {
  type = string
}
variable "cluster_name" {
  type = string
}
variable "service_name" {
  type = string
}
variable "sns_email" {
  type = string
  default = ""
}
variable "tags" {
  type = map(string)
  default = {}
}
