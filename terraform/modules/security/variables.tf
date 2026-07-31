variable "name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "app_port" {
  type    = number
  default = 8000
}

variable "alb_origin_port" {
  type        = number
  description = "Only listener port CloudFront is permitted to reach."
  default     = 80

  validation {
    condition     = contains([80, 443], var.alb_origin_port)
    error_message = "alb_origin_port must be 80 or 443."
  }
}

variable "tags" {
  type    = map(string)
  default = {}
}
