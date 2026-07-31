# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes CloudTrail storage, notification, and observability identifiers.

output "trail_arn" {
  description = "ARN of the multi-region CloudTrail trail."
  value       = aws_cloudtrail.this.arn
}

output "log_bucket_arn" {
  description = "ARN of the encrypted CloudTrail S3 log bucket."
  value       = aws_s3_bucket.logs.arn
}

output "notification_topic_arn" {
  description = "ARN of the encrypted CloudTrail SNS notification topic."
  value       = aws_sns_topic.notifications.arn
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the encrypted CloudTrail CloudWatch log group."
  value       = aws_cloudwatch_log_group.trail.arn
}
