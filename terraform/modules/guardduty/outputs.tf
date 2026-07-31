output "detector_id" {
  value = try(aws_guardduty_detector.this[0].id,null)
}
