data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type = "Service"
      identifiers = ["backup.amazonaws.com"]
    }
  }
}
resource "aws_iam_role" "this" {
  name = "${var.name}-backup"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}
resource "aws_iam_role_policy_attachment" "this" {
  role = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}
resource "aws_backup_vault" "this" {
  name = var.name
  kms_key_arn = var.kms_key_arn
  tags = var.tags
}
resource "aws_backup_plan" "this" {
  name = var.name
  rule {
    rule_name = "daily"
    target_vault_name = aws_backup_vault.this.name
    schedule = "cron(0 5 ? * * *)"
    lifecycle {
      delete_after = 35
    }
  }
  tags = var.tags
}
resource "aws_backup_selection" "this" {
  iam_role_arn = aws_iam_role.this.arn
  name = var.name
  plan_id = aws_backup_plan.this.id
  resources = var.resource_arns
}
