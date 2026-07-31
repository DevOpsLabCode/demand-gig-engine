locals {
  initial_values = { GOOGLE_OAUTH_CLIENT_ID = "", GOOGLE_OAUTH_CLIENT_SECRET = "", FACEBOOK_OAUTH_CLIENT_ID = "", FACEBOOK_OAUTH_CLIENT_SECRET = "", INSTAGRAM_OAUTH_CLIENT_ID = "", INSTAGRAM_OAUTH_CLIENT_SECRET = "", TIKTOK_OAUTH_CLIENT_KEY = "", TIKTOK_OAUTH_CLIENT_SECRET = "", STRIPE_SECRET_KEY = "", STRIPE_WEBHOOK_SECRET = "", META_APP_ID = "", META_APP_SECRET = "", META_PIXEL_ID = "", META_CONVERSIONS_API_TOKEN = "", VIBESMEET_ACCESS_TOKEN = "", VIBESMEET_WEBHOOK_SECRET = "" }
}
resource "aws_secretsmanager_secret" "social" {
  name = "${var.name}/provider-credentials"
  description = "OAuth, payment, Meta, and VibesMeet credentials"
  kms_key_id = var.kms_key_arn
  recovery_window_in_days = 7
  tags = var.tags
}
resource "aws_secretsmanager_secret_version" "initial" {
  secret_id = aws_secretsmanager_secret.social.id
  secret_string = jsonencode(local.initial_values)
  lifecycle {
    ignore_changes = [secret_string]
  }
}
