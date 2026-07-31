variable "name" {
  type = string
}
variable "cluster_arn" {
  type = string
}
variable "subnet_ids" {
  type = list(string)
}
variable "security_group_ids" {
  type = list(string)
}
variable "image" {
  type = string
}
variable "container_port" {
  type = number
  default = 8000
}
variable "expose_port" {
  type = bool
  default = true
}
variable "cpu" {
  type = number
}
variable "memory" {
  type = number
}
variable "desired_count" {
  type = number
}
variable "target_group_arn" {
  type = string
  default = null
}
variable "command" {
  type = list(string)
  default = []
}
variable "environment" {
  type = map(string)
  default = {}
}
variable "secrets" {
  type = map(string)
  default = {}
}
variable "kms_key_arn" {
  type = string
}
variable "queue_arn" {
  type = string
}
variable "object_storage_bucket_arn" {
  type = string
  default = null
}
variable "enable_health_check" {
  type = bool
  default = true
}
variable "enable_autoscaling" {
  type = bool
  default = true
}
variable "log_retention_days" {
  type = number
  default = 30
}
variable "tags" {
  type = map(string)
  default = {}
}

variable "ses_identity_arn" {
  type        = string
  description = "Verified SES identity that tasks may use for outbound mail."
  default     = null
}

variable "enable_xray" {
  type        = bool
  description = "Run the AWS X-Ray daemon sidecar and grant trace write permissions."
  default     = true
}

variable "xray_image" {
  type        = string
  description = "Pinned AWS X-Ray daemon container image."
  default     = "public.ecr.aws/xray/aws-xray-daemon:3.6.6"
}

variable "enable_execute_command" {
  type        = bool
  description = "Enable ECS Exec. Keep false when readonlyRootFilesystem is enabled."
  default     = false
}
