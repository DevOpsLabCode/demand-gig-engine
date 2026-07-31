# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the cloudwatch Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
variable "name" {
  type = string
}
# Input `alb_arn_suffix`: ALB ARN suffix used by CloudWatch dimensions.
variable "alb_arn_suffix" {
  type = string
}
# Input `cluster_name`: Name of the ECS cluster used to construct service and autoscaling identifiers.
variable "cluster_name" {
  type = string
}
# Input `service_name`: Name of the ECS service used by deployment, autoscaling, and monitoring commands.
variable "service_name" {
  type = string
}
# Input `sns_email`: Alarm notification email subscribed to the SNS topic.
variable "sns_email" {
  type = string
  default = ""
}
# Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.
variable "tags" {
  type = map(string)
  default = {}
}
