# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates an encrypted AWS Backup vault, service role, schedule, retention policy, and protected-resource selection.
# Reading guide: Each comment explains why the following Terraform block exists.

# Build the trust policy that permits only the AWS Backup service to assume the backup role.
data "aws_iam_policy_document" "assume" {
  # Allow AWS Backup to assume the service role that protects the selected resources.
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type = "Service"
      identifiers = ["backup.amazonaws.com"]
    }
  }
}
# Creates an IAM role with a narrowly defined trust relationship.
resource "aws_iam_role" "this" {
  name = "${var.name}-backup"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}
# Attaches a managed IAM policy required by the role.
resource "aws_iam_role_policy_attachment" "this" {
  role = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}
# Creates encrypted storage for AWS Backup recovery points.
resource "aws_backup_vault" "this" {
  name = var.name
  kms_key_arn = var.kms_key_arn
  tags = var.tags
}
# Defines backup frequency, retention, and lifecycle policy.
resource "aws_backup_plan" "this" {
  name = var.name
  # Defines one ordered policy or lifecycle rule.
  rule {
    rule_name = "daily"
    target_vault_name = aws_backup_vault.this.name
    schedule = "cron(0 5 ? * * *)"
    # Controls replacement, deletion protection, and drift behavior for this resource.
    lifecycle {
      delete_after = 35
    }
  }
  tags = var.tags
}
# Selects protected resources through the backup service role and tags.
resource "aws_backup_selection" "this" {
  iam_role_arn = aws_iam_role.this.arn
  name = var.name
  plan_id = aws_backup_plan.this.id
  resources = var.resource_arns
}
