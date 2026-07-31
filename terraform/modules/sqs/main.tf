resource "aws_sqs_queue" "dlq" {
  name = "${var.name}-dlq"
  sqs_managed_sse_enabled = true
  message_retention_seconds = 1209600
  tags = var.tags
}
resource "aws_sqs_queue" "tasks" {
  name = "${var.name}-tasks"
  sqs_managed_sse_enabled = true
  visibility_timeout_seconds = 300
  receive_wait_time_seconds = 20
  redrive_policy = jsonencode({ deadLetterTargetArn = aws_sqs_queue.dlq.arn, maxReceiveCount = 5 })
  tags = var.tags
}
