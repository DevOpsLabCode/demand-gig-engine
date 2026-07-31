# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates the Scheduler role and recurring SQS message used to trigger campaign-expiry processing.
# Reading guide: Each comment explains why the following Terraform block exists.

# Build the trust policy that permits only EventBridge Scheduler to assume the queue-delivery role.
data "aws_iam_policy_document" "scheduler_assume" {
  # Allow EventBridge Scheduler to assume the role used to send expiry jobs to SQS.
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}
# Creates an IAM role with a narrowly defined trust relationship.
resource "aws_iam_role" "scheduler" {
  name = "${var.name}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
  tags = var.tags
}
# Attaches least-privilege inline permissions to the IAM role.
resource "aws_iam_role_policy" "scheduler" {
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = [var.queue_arn, var.dlq_arn]
      }
    ]
  })
}
# Creates a logical event channel for future event-driven integrations.
resource "aws_cloudwatch_event_bus" "this" {
  name = var.name
  tags = var.tags
}
# Groups related EventBridge Scheduler definitions for organization and lifecycle management.
resource "aws_scheduler_schedule_group" "this" {
  name = var.name
  tags = var.tags
}
# Invokes the configured target on a managed schedule without running a dedicated cron server.
resource "aws_scheduler_schedule" "campaign_expiry" {
  name = "${var.name}-campaign-expiry"
  group_name = aws_scheduler_schedule_group.this.name
  state = var.schedule_enabled ? "ENABLED" :"DISABLED"
  schedule_expression = var.schedule_expression
  schedule_expression_timezone = "UTC"
  flexible_time_window {
    mode = "OFF"
  }
  # Defines the service invoked by a scheduler, proxy, or routing rule.
  target {
    arn = var.queue_arn
    role_arn = aws_iam_role.scheduler.arn
    input = jsonencode({type = "campaign.expiry.scan"})
    # Sends exhausted failures to a dead-letter destination for investigation.
    dead_letter_config {
      arn = var.dlq_arn
    }
    # Controls retries and maximum event age for failed asynchronous delivery.
    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts = 3
    }
  }
}
