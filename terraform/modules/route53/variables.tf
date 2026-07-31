# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares optional Route 53 alias records for CloudFront or another AWS alias target.

variable "enabled" {
  type        = bool
  description = "Create public alias records."
  default     = false
}

variable "zone_id" {
  type        = string
  description = "Route 53 hosted-zone ID that owns record_name."
  default     = ""

  validation {
    condition     = var.zone_id == "" || can(regex("^Z[A-Z0-9]+$", var.zone_id))
    error_message = "zone_id must be empty or a Route 53 hosted-zone ID."
  }
}

variable "record_name" {
  type        = string
  description = "DNS record name created in the hosted zone."
  default     = ""

  validation {
    condition     = var.record_name == "" || can(regex("^[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\\.?$", var.record_name))
    error_message = "record_name must be empty or a valid DNS name."
  }
}

variable "target_name" {
  type        = string
  description = "AWS alias target DNS name."
  default     = ""

  validation {
    condition     = var.target_name == "" || can(regex("^[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\\.?$", var.target_name))
    error_message = "target_name must be empty or a valid DNS name."
  }
}

variable "target_zone_id" {
  type        = string
  description = "Canonical hosted-zone ID of the alias target."
  default     = ""

  validation {
    condition     = var.target_zone_id == "" || can(regex("^Z[A-Z0-9]+$", var.target_zone_id))
    error_message = "target_zone_id must be empty or a canonical AWS hosted-zone ID."
  }
}

variable "create_ipv6" {
  type        = bool
  description = "Create an AAAA alias in addition to the A alias."
  default     = true
}

check "alias_prerequisites" {
  assert {
    condition     = !var.enabled || alltrue([for value in [var.zone_id, var.record_name, var.target_name, var.target_zone_id] : trimspace(value) != ""])
    error_message = "enabled=true requires zone_id, record_name, target_name, and target_zone_id."
  }
}
