# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares SES identity, DNS authentication, custom MAIL FROM, and DMARC controls.

variable "domain_name" {
  type        = string
  description = "Verified sending domain. May be empty only when create_dns is false."
  default     = ""

  validation {
    condition     = var.domain_name == "" || can(regex("^(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\\.)+[A-Za-z]{2,63}$", var.domain_name))
    error_message = "domain_name must be empty or a valid DNS domain."
  }
}

variable "hosted_zone_id" {
  type        = string
  description = "Route 53 public hosted-zone ID that owns domain_name."
  default     = ""

  validation {
    condition     = var.hosted_zone_id == "" || can(regex("^Z[A-Z0-9]+$", var.hosted_zone_id))
    error_message = "hosted_zone_id must be empty or a Route 53 hosted-zone ID."
  }
}

variable "create_dns" {
  type        = bool
  description = "Create the SES identity and all required Route 53 authentication records."
  default     = false
}

variable "existing_identity_arn" {
  type        = string
  description = "Optional pre-verified SES domain identity ARN used when DNS and identity lifecycle are managed outside this stack."
  default     = null
  nullable    = true

  validation {
    condition     = var.existing_identity_arn == null || can(regex("^arn:[^:]+:ses:[^:]+:[0-9]{12}:identity/", var.existing_identity_arn))
    error_message = "existing_identity_arn must be null or an SES identity ARN."
  }
}

variable "mail_from_subdomain" {
  type        = string
  description = "Subdomain used as the SES custom MAIL FROM domain."
  default     = "mail"

  validation {
    condition     = can(regex("^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", var.mail_from_subdomain))
    error_message = "mail_from_subdomain must be one valid lowercase DNS label."
  }
}

variable "dmarc_policy" {
  type        = string
  description = "DMARC disposition policy. Use quarantine or reject after validating legitimate mail streams."
  default     = "none"

  validation {
    condition     = contains(["none", "quarantine", "reject"], var.dmarc_policy)
    error_message = "dmarc_policy must be none, quarantine, or reject."
  }
}

variable "dmarc_percentage" {
  type        = number
  description = "Percentage of messages to which the DMARC policy applies."
  default     = 100

  validation {
    condition     = floor(var.dmarc_percentage) == var.dmarc_percentage && var.dmarc_percentage >= 0 && var.dmarc_percentage <= 100
    error_message = "dmarc_percentage must be a whole number from 0 through 100."
  }
}

variable "dmarc_rua" {
  type        = string
  description = "Optional aggregate-report mailbox without the mailto: prefix."
  default     = ""

  validation {
    condition     = var.dmarc_rua == "" || can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.dmarc_rua))
    error_message = "dmarc_rua must be empty or a valid email address."
  }
}

check "dns_prerequisites" {
  assert {
    condition     = !var.create_dns || (var.domain_name != "" && var.hosted_zone_id != "")
    error_message = "create_dns=true requires domain_name and hosted_zone_id."
  }
}


check "identity_source" {
  assert {
    condition     = !(var.create_dns && var.existing_identity_arn != null)
    error_message = "Use either Terraform-managed SES DNS identity creation or existing_identity_arn, not both."
  }
}
