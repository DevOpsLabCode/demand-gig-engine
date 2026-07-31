# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates secure S3 remote-state storage before the main environment can use that backend.
# Reading guide: Each comment explains why the following Terraform block exists.

# Read the active AWS account identity for policies, names, and ownership checks.
data "aws_caller_identity" "current" {
}
# Creates an encrypted object-storage bucket for static assets, media, logs, or state.
resource "aws_s3_bucket" "state" {
  bucket = "${var.project_name}-${var.environment}-${data.aws_caller_identity.current.account_id}-tfstate"
}
# Retains prior object versions to support recovery and auditability.
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  # Enables or suspends object versioning.
  versioning_configuration {
    status = "Enabled"
  }
}
# Prevents accidental public exposure through S3 ACLs or policies.
resource "aws_s3_bucket_public_access_block" "state" {
  bucket = aws_s3_bucket.state.id
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}
# Enforces server-side encryption for newly written objects.
resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  # Defines one ordered policy or lifecycle rule.
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
# Applies resource-level access controls and transport requirements to the bucket.
resource "aws_s3_bucket_policy" "tls" {
  bucket = aws_s3_bucket.state.id
  policy = jsonencode({Version = "2012-10-17",Statement = [{Sid = "DenyInsecureTransport",Effect = "Deny",Principal = "*",Action = "s3:*",Resource = [aws_s3_bucket.state.arn,"${aws_s3_bucket.state.arn}/*"],Condition = {Bool = {"aws:SecureTransport" = "false"}}}]})
}
# Output `bucket`: Name of the remote-state S3 bucket created or validated by the bootstrap stack.
output "bucket" {
  value = aws_s3_bucket.state.id
}
