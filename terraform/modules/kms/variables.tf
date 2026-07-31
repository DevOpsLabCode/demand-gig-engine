variable "name" {
  type = string
}
variable "deletion_window" {
  type = number
  default = 30
}
variable "tags" {
  type = map(string)
  default = {}
}
