# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes queue URLs, ARNs, and names used by application, scheduler, IAM, and monitoring modules.

output "queue_url" {
  description = "SQS queue URL consumed by the worker process."
  value       = aws_sqs_queue.tasks.url
}

output "queue_arn" {
  description = "Source queue ARN used by ECS and EventBridge Scheduler IAM policies."
  value       = aws_sqs_queue.tasks.arn
}

output "queue_name" {
  description = "Source queue name used by CloudWatch alarm dimensions."
  value       = aws_sqs_queue.tasks.name
}

output "dlq_arn" {
  description = "Dead-letter queue ARN used by EventBridge Scheduler and redrive policies."
  value       = aws_sqs_queue.dlq.arn
}

output "dlq_name" {
  description = "Dead-letter queue name used by CloudWatch alarm dimensions."
  value       = aws_sqs_queue.dlq.name
}
