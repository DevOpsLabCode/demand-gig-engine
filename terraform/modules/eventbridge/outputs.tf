output "event_bus_arn" {
  value = aws_cloudwatch_event_bus.this.arn
}
output "schedule_arn" {
  value = aws_scheduler_schedule.campaign_expiry.arn
}
