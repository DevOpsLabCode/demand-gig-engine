
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates an encrypted EventBridge Scheduler invocation that sends campaign-expiry work to SQS.

data "aws_iam_policy_document" "scheduler_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  permissions_boundary = var.permissions_boundary_arn
  name                 = "${var.name}-scheduler"
  assume_role_policy   = data.aws_iam_policy_document.scheduler_assume.json
  tags                 = var.tags
}

resource "aws_iam_role_policy" "scheduler" {
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = [var.queue_arn, var.dlq_arn]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt", "kms:GenerateDataKey"]
        Resource = var.kms_key_arn
      }
    ]
  })
}

resource "aws_scheduler_schedule_group" "this" {
  name = var.name
  tags = var.tags
}

resource "aws_scheduler_schedule" "campaign_expiry" {
  name                         = "${var.name}-campaign-expiry"
  group_name                   = aws_scheduler_schedule_group.this.name
  state                        = var.schedule_enabled ? "ENABLED" : "DISABLED"
  schedule_expression          = var.schedule_expression
  schedule_expression_timezone = "UTC"
  kms_key_arn                  = var.kms_key_arn

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = var.queue_arn
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ type = "campaign.expiry.scan" })

    dead_letter_config {
      arn = var.dlq_arn
    }

    retry_policy {
      maximum_event_age_in_seconds = var.maximum_event_age_seconds
      maximum_retry_attempts       = var.maximum_retry_attempts
    }
  }
}
