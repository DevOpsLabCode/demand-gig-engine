# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares DNS-validated certificate creation and optional existing-certificate reuse.

variable "domain_name" {
  type        = string
  description = "Primary certificate name. Empty is permitted only when certificate creation is disabled."
  default     = ""

  validation {
    condition     = var.domain_name == "" || can(regex("^(\\*\\.)?[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$", var.domain_name))
    error_message = "domain_name must be empty or a valid DNS name, optionally beginning with *."
  }
}

variable "subject_alternative_names" {
  type        = list(string)
  description = "Additional certificate names."
  default     = []

  validation {
    condition     = alltrue([for name in var.subject_alternative_names : can(regex("^(\\*\\.)?[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$", name))])
    error_message = "subject_alternative_names must contain valid DNS names."
  }
}

variable "hosted_zone_id" {
  type        = string
  description = "Route 53 hosted zone used for DNS validation."
  default     = ""

  validation {
    condition     = var.hosted_zone_id == "" || can(regex("^Z[A-Z0-9]+$", var.hosted_zone_id))
    error_message = "hosted_zone_id must be empty or a Route 53 hosted-zone ID."
  }
}

variable "create" {
  type        = bool
  description = "Create and DNS-validate a certificate in this module."
  default     = false
}

variable "existing_certificate_arn" {
  type        = string
  description = "Existing ACM certificate ARN used when create is false; null leaves TLS certificate selection to the caller."
  default     = null
  nullable    = true

  validation {
    condition     = var.existing_certificate_arn == null || can(regex("^arn:[^:]+:acm:[^:]+:[0-9]{12}:certificate/", var.existing_certificate_arn))
    error_message = "existing_certificate_arn must be null or an ACM certificate ARN."
  }
}

variable "tags" {
  type        = map(string)
  description = "Common ownership, environment, cost, and governance tags."
  default     = {}
}

check "certificate_source" {
  assert {
    condition     = !var.create || (trimspace(var.domain_name) != "" && trimspace(var.hosted_zone_id) != "" && var.existing_certificate_arn == null)
    error_message = "create=true requires domain_name and hosted_zone_id and cannot be combined with existing_certificate_arn."
  }
}
