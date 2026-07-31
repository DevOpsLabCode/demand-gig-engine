# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes reusable values produced by the eventbridge Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Output `event_bus_arn`: ARN of the event bus resource consumed by this module.
output "event_bus_arn" {
  value = aws_cloudwatch_event_bus.this.arn
}
# Output `schedule_arn`: ARN of the schedule resource consumed by this module.
output "schedule_arn" {
  value = aws_scheduler_schedule.campaign_expiry.arn
}
