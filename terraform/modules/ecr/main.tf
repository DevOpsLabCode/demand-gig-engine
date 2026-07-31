# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates immutable, encrypted container repositories with lifecycle cleanup and vulnerability scanning.
# Reading guide: Each comment explains why the following Terraform block exists.

# Create and manage the aws ecr repository resource owned by this file.
resource "aws_ecr_repository" "this" {
  for_each = var.repositories
  name = "${var.name}-${each.key}"
  image_tag_mutability = "IMMUTABLE"
  encryption_configuration {
    encryption_type = "KMS"
    kms_key = var.kms_key_arn
  }
  image_scanning_configuration {
    scan_on_push = true
  }
  tags = var.tags
}
# Removes superseded images while retaining a safe rollback window.
resource "aws_ecr_lifecycle_policy" "this" {
  for_each = aws_ecr_repository.this
  repository = each.value.name
  policy = jsonencode({rules = [{rulePriority = 1,description = "Keep 30 images",selection = {tagStatus = "any",countType = "imageCountMoreThan",countNumber = 30},action = {type = "expire"}}]})
}
