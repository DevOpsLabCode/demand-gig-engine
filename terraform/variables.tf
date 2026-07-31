# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares configurable environment, networking, scaling, DNS, security, and integration inputs for the root stack.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `project_name`: Stable project prefix used to name and tag shared AWS resources.
variable "project_name" {
  type        = string
  description = "Stable lowercase project prefix used in AWS resource names and account-foundation contracts."
  default     = "demand-gig-engine"

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.project_name))
    error_message = "project_name must be 3-63 lowercase alphanumeric or hyphen characters."
  }
}
# Input `environment`: Deployment environment name or the container environment-variable map, according to module context.
variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment must be dev or prod"
  }
}
# Input `aws_region`: AWS region in which regional workload resources are created.
variable "aws_region" {
  type        = string
  description = "AWS region in which regional workload resources are created."
  default     = "us-east-1"

  validation {
    condition     = can(regex("^[a-z]{2}(-gov)?-[a-z]+-[0-9]+$", var.aws_region))
    error_message = "aws_region must be a valid AWS region name."
  }
}
# Input `domain_name`: Fully qualified DNS name exposed by the service.
variable "domain_name" {
  type    = string
  default = ""
}
# Input `hosted_zone_id`: Route 53 hosted-zone ID in which DNS records are created.
variable "hosted_zone_id" {
  type    = string
  default = ""
}
# Input `create_dns`: Whether Terraform should create the dns resource or record.
variable "create_dns" {
  type    = bool
  default = false
}
# Input `vpc_cidr`: Private IPv4 CIDR allocated to the VPC; subnet CIDRs are derived from this range.
variable "vpc_cidr" {
  type = string
  validation {
    condition     = can(cidrnetmask(var.vpc_cidr))
    error_message = "vpc_cidr must be a valid IPv4 CIDR block"
  }
}
# Input `az_count`: Number of Availability Zones across which subnet tiers are created.
variable "az_count" {
  type    = number
  default = 2
  validation {
    condition     = var.az_count >= 2 && var.az_count <= 3
    error_message = "az_count must be 2 or 3"
  }
}
# Input `nat_gateway_per_az`: Whether each application Availability Zone receives its own NAT gateway for resilience.
variable "nat_gateway_per_az" {
  type    = bool
  default = false
}
# Input `backend_image`: ECR image URI and tag/digest launched by the API ECS task.
variable "backend_image" {
  type = string
  validation {
    condition     = trimspace(var.backend_image) != ""
    error_message = "backend_image must not be empty"
  }
}
# Input `backend_cpu`: Fargate CPU units reserved for each API task.
variable "backend_cpu" {
  type    = number
  default = 512
}
# Input `backend_memory`: Memory in MiB reserved for each API task.
variable "backend_memory" {
  type    = number
  default = 1024
}
# Input `backend_desired_count`: Steady-state number of API tasks requested after migrations complete.
variable "backend_desired_count" {
  type    = number
  default = 1
}
# Input `allow_zero_capacity`: Permit services to start at zero tasks during staged image publication and database migration.
variable "allow_zero_capacity" {
  type    = bool
  default = false
}
# Input `worker_cpu`: Fargate CPU units reserved for each asynchronous worker task.
variable "worker_cpu" {
  type    = number
  default = 512
}
# Input `worker_memory`: Memory in MiB reserved for each asynchronous worker task.
variable "worker_memory" {
  type    = number
  default = 1024
}
# Input `worker_desired_count`: Steady-state number of SQS worker tasks requested after migrations complete.
variable "worker_desired_count" {
  type    = number
  default = 1
}
# Input `db_instance_class`: RDS PostgreSQL compute and memory class.
variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}
# Input `db_allocated_storage`: Initial encrypted PostgreSQL storage allocation in GiB.
variable "db_allocated_storage" {
  type    = number
  default = 20
}
# Input `db_multi_az`: Create a synchronous standby in another Availability Zone for production resilience.
variable "db_multi_az" {
  type    = bool
  default = true
}
# Input `redis_node_type`: ElastiCache node class used by the Redis replication group.
variable "redis_node_type" {
  type    = string
  default = "cache.t4g.micro"
}
# Input `redis_replicas`: Number of Redis read replicas; at least one is required for Multi-AZ automatic failover.
variable "redis_replicas" {
  type    = number
  default = 1

  validation {
    condition     = floor(var.redis_replicas) == var.redis_replicas && var.redis_replicas >= 1 && var.redis_replicas <= 5
    error_message = "redis_replicas must be a whole number between 1 and 5."
  }
}
# Input `deletion_protection`: Whether the managed service rejects accidental deletion.
variable "deletion_protection" {
  type    = bool
  default = true
}
# Input `schedule_enabled`: Whether the campaign-expiry schedule is active.
variable "schedule_enabled" {
  type    = bool
  default = true
}
# Input `enable_guardduty`: Whether to enable guardduty behavior.
variable "enable_guardduty" {
  type    = bool
  default = true
}
# Input `payment_provider`: Backend payment adapter selected at runtime, such as fake for development or Stripe for real deposits.
variable "payment_provider" {
  type    = string
  default = "fake"
}
# Input `cloudfront_price_class`: CloudFront edge-location price class controlling geographic coverage and cost.
variable "cloudfront_price_class" {
  type    = string
  default = "PriceClass_100"
}
# Input `cloudtrail_retention_days`: Number of days used for cloudtrail retention retention or timing.
variable "cloudtrail_retention_days" {
  type    = number
  default = 365
}
# Input `github_org`: GitHub organization embedded in the trusted OIDC subject patterns.
variable "github_org" {
  type    = string
  default = "DevOpsLabCode"
}
# Input `github_repo`: GitHub repository embedded in the trusted OIDC subject patterns.
variable "github_repo" {
  type    = string
  default = "demand-gig-engine"
}
# Optional existing SES identity when DNS/email authentication is managed outside this stack.
variable "ses_identity_arn" {
  type        = string
  description = "Existing verified SES domain identity ARN used when create_dns is false."
  default     = null
  nullable    = true

  validation {
    condition     = var.ses_identity_arn == null || can(regex("^arn:[^:]+:ses:[^:]+:[0-9]{12}:identity/", var.ses_identity_arn))
    error_message = "ses_identity_arn must be null or a valid SES identity ARN."
  }
}

# Input `alarm_email`: Email endpoint subscribed to the operational SNS alarm topic.
variable "alarm_email" {
  type        = string
  description = "Optional operational alert and DMARC aggregate-report mailbox."
  default     = ""

  validation {
    condition     = var.alarm_email == "" || can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.alarm_email))
    error_message = "alarm_email must be empty or a syntactically valid email address."
  }
}
# Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.
variable "tags" {
  type    = map(string)
  default = {}
}

# Optional existing ACM certificate in us-east-1 for the CloudFront viewer alias.
variable "viewer_certificate_arn" {
  type        = string
  description = "Existing us-east-1 ACM certificate ARN used when DNS validation is managed outside this stack."
  default     = null
  nullable    = true

  validation {
    condition     = var.viewer_certificate_arn == null || can(regex("^arn:[^:]+:acm:us-east-1:[0-9]{12}:certificate/", var.viewer_certificate_arn))
    error_message = "viewer_certificate_arn must be null or an us-east-1 ACM certificate ARN."
  }
}

# Optional existing regional ACM certificate for encrypted CloudFront-to-ALB traffic.
variable "origin_certificate_arn" {
  type        = string
  description = "Existing regional ACM certificate ARN for origin.domain_name when DNS validation is external."
  default     = null
  nullable    = true

  validation {
    condition     = var.origin_certificate_arn == null || can(regex("^arn:[^:]+:acm:[^:]+:[0-9]{12}:certificate/", var.origin_certificate_arn))
    error_message = "origin_certificate_arn must be null or an ACM certificate ARN."
  }
}

variable "enable_backup_vault_lock" {
  type        = bool
  description = "Enable Compliance-mode AWS Backup Vault Lock. Use true for production and false for disposable development."
  default     = false
}

variable "backup_retention_days" {
  type        = number
  description = "Recovery-point retention and Vault Lock minimum retention."
  default     = 35

  validation {
    condition     = floor(var.backup_retention_days) == var.backup_retention_days && var.backup_retention_days >= 1
    error_message = "backup_retention_days must be a positive whole number."
  }
}

variable "backup_max_retention_days" {
  type        = number
  description = "Maximum retention accepted by Vault Lock."
  default     = 3650

  validation {
    condition     = floor(var.backup_max_retention_days) == var.backup_max_retention_days && var.backup_max_retention_days >= var.backup_retention_days
    error_message = "backup_max_retention_days must be at least backup_retention_days."
  }
}

variable "backup_cold_storage_after_days" {
  type        = number
  description = "Days before AWS Backup cold storage transition; null disables transition."
  default     = null
  nullable    = true
}

variable "backup_vault_lock_changeable_days" {
  type        = number
  description = "Grace period before Compliance-mode Vault Lock becomes immutable."
  default     = 3
}

variable "enforce_production_readiness" {
  type        = bool
  description = "Fail production plans that still use fake payments, omit alarms, or lack a custom TLS domain."
  default     = false
}
