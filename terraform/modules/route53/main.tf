# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates optional IPv4/IPv6 alias records that map the application hostname to CloudFront or the ALB.
# Reading guide: Each comment explains why the following Terraform block exists.

# Create and manage the aws route53 record resource owned by this file.
resource "aws_route53_record" "ipv4" {
  count   = var.enabled ? 1 : 0
  zone_id = var.zone_id
  name    = var.record_name
  type    = "A"
  # Associates the service endpoint with a DNS alias target.
  alias {
    name                   = var.target_name
    zone_id                = var.target_zone_id
    evaluate_target_health = false
  }
}
# Creates the DNS record used for validation or service routing.
resource "aws_route53_record" "ipv6" {
  count   = var.enabled && var.create_ipv6 ? 1 : 0
  zone_id = var.zone_id
  name    = var.record_name
  type    = "AAAA"
  # Associates the service endpoint with a DNS alias target.
  alias {
    name                   = var.target_name
    zone_id                = var.target_zone_id
    evaluate_target_health = false
  }
}
