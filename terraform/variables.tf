variable "project_name" {
  type = string
  default = "demand-gig-engine"
}
variable "environment" {
  type = string
  validation {
    condition = contains(["dev","prod"],var.environment)
    error_message = "environment must be dev or prod"
  }
}
variable "aws_region" {
  type = string
  default = "us-east-1"
}
variable "domain_name" {
  type = string
  default = ""
}
variable "hosted_zone_id" {
  type = string
  default = ""
}
variable "create_dns" {
  type = bool
  default = false
}
variable "vpc_cidr" {
  type = string
  validation {
    condition = can(cidrnetmask(var.vpc_cidr))
    error_message = "vpc_cidr must be a valid IPv4 CIDR block"
  }
}
variable "az_count" {
  type = number
  default = 2
  validation {
    condition = var.az_count >= 2 && var.az_count <= 3
    error_message = "az_count must be 2 or 3"
  }
}
variable "nat_gateway_per_az" {
  type = bool
  default = false
}
variable "backend_image" {
  type = string
  validation {
    condition = trimspace(var.backend_image) != ""
    error_message = "backend_image must not be empty"
  }
}
variable "backend_cpu" {
  type = number
  default = 512
}
variable "backend_memory" {
  type = number
  default = 1024
}
variable "backend_desired_count" {
  type = number
  default = 1
}
variable "allow_zero_capacity" {
  type = bool
  default = false
}
variable "worker_cpu" {
  type = number
  default = 512
}
variable "worker_memory" {
  type = number
  default = 1024
}
variable "worker_desired_count" {
  type = number
  default = 1
}
variable "db_instance_class" {
  type = string
  default = "db.t4g.micro"
}
variable "db_allocated_storage" {
  type = number
  default = 20
}
variable "db_multi_az" {
  type = bool
  default = false
}
variable "redis_node_type" {
  type = string
  default = "cache.t4g.micro"
}
variable "redis_replicas" {
  type = number
  default = 0
}
variable "deletion_protection" {
  type = bool
  default = false
}
variable "schedule_enabled" {
  type = bool
  default = true
}
variable "enable_guardduty" {
  type = bool
  default = true
}
variable "payment_provider" {
  type = string
  default = "fake"
}
variable "cloudfront_price_class" {
  type = string
  default = "PriceClass_100"
}
variable "cloudtrail_retention_days" {
  type = number
  default = 365
}
variable "github_org" {
  type = string
  default = "DevOpsLabCode"
}
variable "github_repo" {
  type = string
  default = "demand-gig-engine"
}
variable "alarm_email" {
  type = string
  default = ""
}
variable "tags" {
  type = map(string)
  default = {}
}

variable "db_performance_insights_enabled" {
  type        = bool
  description = "Enable RDS Performance Insights on supported production instance classes."
  default     = false
}

variable "enable_execute_command" {
  type        = bool
  description = "Enable ECS Exec. Disabled by default because it is incompatible with a read-only root filesystem."
  default     = false
}

variable "create_github_oidc_provider" {
  type        = bool
  description = "Create the account-global GitHub OIDC provider. Set false only when another stack in the same AWS account owns it."
  default     = true
}
