# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates the ECS cluster, Container Insights settings, and encrypted ECS Exec audit logging.
# Reading guide: Each comment explains why the following Terraform block exists.

# Create and manage the aws ecs cluster resource owned by this file.
resource "aws_ecs_cluster" "this" {
  name = var.name
  setting {
    name = "containerInsights"
    value = "enhanced"
  }
  # Defines the service-specific nested configuration values.
  configuration {
    # Configures audited ECS Exec access for emergency diagnostics.
    execute_command_configuration {
      kms_key_id = var.kms_key_arn
      logging = "OVERRIDE"
      log_configuration {
        cloud_watch_encryption_enabled = true
        cloud_watch_log_group_name = aws_cloudwatch_log_group.exec.name
      }
    }
  }
  tags = var.tags
}
# Stores application, task, or ECS Exec logs with controlled retention.
resource "aws_cloudwatch_log_group" "exec" {
  name = "/aws/ecs/${var.name}/exec"
  retention_in_days = 30
  kms_key_id = var.kms_key_arn
  tags = var.tags
}
