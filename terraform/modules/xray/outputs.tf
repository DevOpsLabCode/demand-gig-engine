# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes the sampling rule for trace-governance tooling.

output "sampling_rule_arn" {
  description = "ARN of the X-Ray sampling rule."
  value       = aws_xray_sampling_rule.this.arn
}

output "sampling_rule_name" {
  description = "Name of the X-Ray sampling rule."
  value       = aws_xray_sampling_rule.this.rule_name
}
