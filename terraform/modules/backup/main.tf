
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates an encrypted AWS Backup vault, immutable retention controls, schedule, role, and protected-resource selection.

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["backup.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "this" {
  name               = "${var.name}-backup"
  assume_role_policy = data.aws_iam_policy_document.assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "this" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

# Grant the backup service role access only to this environment's vault key.
# CreateGrant is constrained to grants created for AWS-managed resources.
resource "aws_iam_role_policy" "kms" {
  name = "${var.name}-backup-kms"
  role = aws_iam_role.this.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "UseBackupVaultKey"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:Encrypt",
          "kms:GenerateDataKey*",
          "kms:ReEncrypt*",
        ]
        Resource = var.kms_key_arn
      },
      {
        Sid      = "CreateAWSResourceGrant"
        Effect   = "Allow"
        Action   = ["kms:CreateGrant"]
        Resource = var.kms_key_arn
        Condition = {
          Bool = {
            "kms:GrantIsForAWSResource" = "true"
          }
        }
      },
    ]
  })
}

resource "aws_backup_vault" "this" {
  name        = var.name
  kms_key_arn = var.kms_key_arn
  tags        = var.tags
}

# Vault Lock prevents recovery points from being shortened or deleted before the
# configured minimum. The grace period permits correction of a mistaken first apply.
resource "aws_backup_vault_lock_configuration" "this" {
  backup_vault_name   = aws_backup_vault.this.name
  changeable_for_days = var.vault_lock_changeable_for_days
  min_retention_days  = var.minimum_retention_days
  max_retention_days  = var.maximum_retention_days
}

resource "aws_backup_plan" "this" {
  name = var.name

  rule {
    rule_name         = "daily"
    target_vault_name = aws_backup_vault.this.name
    schedule          = "cron(0 5 ? * * *)"

    lifecycle {
      cold_storage_after = var.cold_storage_after_days
      delete_after       = var.minimum_retention_days
    }
  }

  tags = var.tags
}

resource "aws_backup_selection" "this" {
  iam_role_arn = aws_iam_role.this.arn
  name         = var.name
  plan_id      = aws_backup_plan.this.id
  resources    = var.resource_arns
}
