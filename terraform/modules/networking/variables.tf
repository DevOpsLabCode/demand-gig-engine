variable "name" {
  type = string
}
variable "cidr" {
  type = string
}
variable "az_count" {
  type = number
}
variable "nat_gateway_per_az" {
  type = bool
  default = false
}
variable "tags" {
  type = map(string)
  default = {}
}
