resource "aws_guardduty_detector" "this" {
  count = var.enabled ? 1 :0
  enable = true
  finding_publishing_frequency = "FIFTEEN_MINUTES"
  tags = var.tags
}
