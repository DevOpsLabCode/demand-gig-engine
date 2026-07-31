# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares X-Ray sampling scope and cost-control inputs.

variable "name" {
  type        = string
  description = "Unique X-Ray sampling-rule name."

  validation {
    condition     = length(trimspace(var.name)) >= 3 && length(var.name) <= 32
    error_message = "name must contain 3-32 characters."
  }
}

variable "priority" {
  type        = number
  description = "Rule priority; lower numbers are evaluated first."
  default     = 9000

  validation {
    condition     = floor(var.priority) == var.priority && var.priority >= 1 && var.priority <= 9999
    error_message = "priority must be a whole number from 1 through 9999."
  }
}

variable "reservoir_size" {
  type        = number
  description = "Guaranteed traces sampled each second before fixed-rate sampling."
  default     = 1

  validation {
    condition     = floor(var.reservoir_size) == var.reservoir_size && var.reservoir_size >= 0
    error_message = "reservoir_size must be a non-negative whole number."
  }
}

variable "fixed_rate" {
  type        = number
  description = "Sampling probability after the reservoir is exhausted."
  default     = 0.05

  validation {
    condition     = var.fixed_rate >= 0 && var.fixed_rate <= 1
    error_message = "fixed_rate must be between 0 and 1."
  }
}

variable "url_path" {
  type        = string
  description = "URL path pattern matched by the rule."
  default     = "*"
}

variable "host" {
  type        = string
  description = "Host pattern matched by the rule."
  default     = "*"
}

variable "http_method" {
  type        = string
  description = "HTTP method pattern matched by the rule."
  default     = "*"
}

variable "service_type" {
  type        = string
  description = "X-Ray service type pattern matched by the rule."
  default     = "*"
}

variable "service_name" {
  type        = string
  description = "X-Ray service name pattern matched by the rule."
  default     = "*"
}

variable "resource_arn" {
  type        = string
  description = "Resource ARN pattern matched by the rule."
  default     = "*"
}
