# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the ecs service Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
variable "name" {
  type = string
}
# Input `cluster_arn`: ARN of the ECS cluster that will run this service.
variable "cluster_arn" {
  type = string
}
# Input `subnet_ids`: Subnet IDs that determine the private or public network placement of the resource.
variable "subnet_ids" {
  type = list(string)
}
# Input `security_group_ids`: Security groups attached to the workload network interface.
variable "security_group_ids" {
  type = list(string)
}
# Input `image`: Container image URI and tag or digest launched by the task definition.
variable "image" {
  type = string
}
# Input `container_port`: TCP port on which the application container listens.
variable "container_port" {
  type = number
  default = 8000
}
# Input `expose_port`: Whether the ECS service should register the application port and load-balancer mapping.
variable "expose_port" {
  type = bool
  default = true
}
# Input `cpu`: Fargate CPU units reserved by the task definition.
variable "cpu" {
  type = number
}
# Input `memory`: Memory in MiB reserved by the task definition.
variable "memory" {
  type = number
}
# Input `desired_count`: Number of service tasks Terraform requests at steady state.
variable "desired_count" {
  type = number
}
# Input `target_group_arn`: Optional ALB target-group ARN used to register this ECS service.
variable "target_group_arn" {
  type = string
  default = null
}
# Input `command`: Optional container command that overrides the image default.
variable "command" {
  type = list(string)
  default = []
}
# Input `environment`: Deployment environment name or the container environment-variable map, according to module context.
variable "environment" {
  type = map(string)
  default = {}
}
# Input `secrets`: Map of container environment names to Secrets Manager or Parameter Store value ARNs.
variable "secrets" {
  type = map(string)
  default = {}
}
# Input `kms_key_arn`: Customer-managed KMS key ARN used to encrypt supported data, logs, queues, or secrets.
variable "kms_key_arn" {
  type = string
}
# Input `queue_arn`: SQS queue ARN the task may read from or publish to.
variable "queue_arn" {
  type = string
}
# Input `object_storage_bucket_arn`: Optional S3 bucket ARN the task may access for private application objects.
variable "object_storage_bucket_arn" {
  type = string
  default = null
}
# Input `enable_health_check`: Whether the task definition includes the application container health check.
variable "enable_health_check" {
  type = bool
  default = true
}
# Input `enable_autoscaling`: Whether Application Auto Scaling resources are created for the service.
variable "enable_autoscaling" {
  type = bool
  default = true
}
# Input `log_retention_days`: Number of days CloudWatch retains logs before automatic expiration.
variable "log_retention_days" {
  type        = number
  description = "CloudWatch application-log retention; one year is the security baseline."
  default     = 365

  validation {
    condition     = var.log_retention_days >= 365
    error_message = "Application logs must be retained for at least 365 days."
  }
}
# Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.
variable "tags" {
  type = map(string)
  default = {}
}

# Input `ses_identity_arn`: Verified SES identity that tasks may use for outbound mail.
variable "ses_identity_arn" {
  type        = string
  description = "Verified SES identity that tasks may use for outbound mail."
  default     = null
}

# Input `enable_xray`: Run the AWS X-Ray daemon sidecar and grant trace write permissions.
variable "enable_xray" {
  type        = bool
  description = "Run the AWS X-Ray daemon sidecar and grant trace write permissions."
  default     = true
}

# Input `xray_image`: Pinned AWS X-Ray daemon container image.
variable "xray_image" {
  type        = string
  description = "Pinned AWS X-Ray daemon container image."
  default     = "public.ecr.aws/xray/aws-xray-daemon:3.x"
}
