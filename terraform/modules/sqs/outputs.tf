# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes reusable values produced by the sqs Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Output `queue_url`: SQS queue URL consumed by the worker process.
output "queue_url" {
  value = aws_sqs_queue.tasks.url
}
# Output `queue_arn`: SQS queue ARN the task may read from or publish to.
output "queue_arn" {
  value = aws_sqs_queue.tasks.arn
}
# Output `dlq_arn`: Dead-letter queue ARN that receives messages after retries are exhausted.
output "dlq_arn" {
  value = aws_sqs_queue.dlq.arn
}
