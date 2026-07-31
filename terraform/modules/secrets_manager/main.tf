# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates the encrypted application secret container and a stable initial secret version.
# Reading guide: Each comment explains why the following Terraform block exists.

# Compute reusable derived values used throughout this file.
locals {
  initial_values = { GOOGLE_OAUTH_CLIENT_ID = "", GOOGLE_OAUTH_CLIENT_SECRET = "", FACEBOOK_OAUTH_CLIENT_ID = "", FACEBOOK_OAUTH_CLIENT_SECRET = "", INSTAGRAM_OAUTH_CLIENT_ID = "", INSTAGRAM_OAUTH_CLIENT_SECRET = "", TIKTOK_OAUTH_CLIENT_KEY = "", TIKTOK_OAUTH_CLIENT_SECRET = "", STRIPE_SECRET_KEY = "", STRIPE_WEBHOOK_SECRET = "", META_APP_ID = "", META_APP_SECRET = "", META_PIXEL_ID = "", META_CONVERSIONS_API_TOKEN = "", VIBESMEET_ACCESS_TOKEN = "", VIBESMEET_WEBHOOK_SECRET = "" }
}

resource "aws_secretsmanager_secret" "social" {
  #checkov:skip=CKV2_AWS_57:Third-party credentials must first be rotated with Google, Meta, Stripe, TikTok, and VibesMeet, then atomically promoted by the provider-credential runbook.
  name = "${var.name}/provider-credentials"
  description = "OAuth, payment, Meta, and VibesMeet credentials"
  kms_key_id = var.kms_key_arn
  recovery_window_in_days = var.recovery_window_in_days
  tags = var.tags
}
# Initializes or updates the JSON value stored in Secrets Manager.
resource "aws_secretsmanager_secret_version" "initial" {
  secret_id = aws_secretsmanager_secret.social.id
  secret_string = jsonencode(local.initial_values)
  # Controls replacement, deletion protection, and drift behavior for this resource.
  lifecycle {
    ignore_changes = [secret_string]
  }
}
