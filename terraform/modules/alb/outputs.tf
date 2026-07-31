# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes reusable values produced by the alb Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Output `arn`: ARN of the Application Load Balancer for IAM, monitoring, and cross-module references.
output "arn" {
  value = aws_lb.this.arn
}
# Output `dns_name`: AWS-generated ALB hostname used by Route 53 and the CloudFront origin.
output "dns_name" {
  value = aws_lb.this.dns_name
}
# Output `zone_id`: AWS hosted-zone identifier required by an alias target.
output "zone_id" {
  value = aws_lb.this.zone_id
}
# Output `target_group_arn`: Optional ALB target-group ARN used to register this ECS service.
output "target_group_arn" {
  value = aws_lb_target_group.backend.arn
}
