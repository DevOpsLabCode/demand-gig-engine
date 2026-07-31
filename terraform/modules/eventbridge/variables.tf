# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares the input contract for the eventbridge Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Input `name`: Stable name prefix used for resource names, logs, tags, and service identifiers.
variable "name" {
  type = string
}
# Input `queue_arn`: SQS queue ARN the task may read from or publish to.
variable "queue_arn" {
  type = string
}
# Input `dlq_arn`: Dead-letter queue ARN that receives messages after retries are exhausted.
variable "dlq_arn" {
  type = string
}
# Input `schedule_enabled`: Whether the campaign-expiry schedule is active.
variable "schedule_enabled" {
  type = bool
  default = true
}
# Input `schedule_expression`: EventBridge Scheduler expression controlling when the campaign-expiry job runs.
variable "schedule_expression" {
  type = string
  default = "rate(5 minutes)"
}
# Input `tags`: Common ownership, environment, cost, and governance tags applied to supported resources.
variable "tags" {
  type = map(string)
  default = {}
}
