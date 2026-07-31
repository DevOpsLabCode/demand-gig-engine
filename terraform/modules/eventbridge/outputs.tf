# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes Scheduler identifiers for operations and audit tooling.

output "schedule_arn" {
  description = "Campaign-expiry Scheduler ARN."
  value       = aws_scheduler_schedule.campaign_expiry.arn
}

output "schedule_group_name" {
  description = "Scheduler group name."
  value       = aws_scheduler_schedule_group.this.name
}
