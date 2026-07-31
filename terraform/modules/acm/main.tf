# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Requests and DNS-validates an ACM certificate, or reuses a supplied certificate ARN when creation is disabled.
# Reading guide: Each comment explains why the following Terraform block exists.

# Create and manage the aws acm certificate resource owned by this file.
resource "aws_acm_certificate" "this" {
  count = var.create ? 1 :0
  domain_name = var.domain_name
  subject_alternative_names = var.subject_alternative_names
  validation_method = "DNS"
  # Controls replacement, deletion protection, and drift behavior for this resource.
  lifecycle {
    create_before_destroy = true
  }
  tags = var.tags
}
# Creates the DNS record used for validation or service routing.
resource "aws_route53_record" "validation" {
  for_each = var.create ? {for option in aws_acm_certificate.this[0].domain_validation_options :option.domain_name => { name = option.resource_record_name, record = option.resource_record_value, type = option.resource_record_type }} :{}
  allow_overwrite = true
  zone_id = var.hosted_zone_id
  name = each.value.name
  type = each.value.type
  ttl = 60
  records = [each.value.record]
}
# Waits for DNS validation before dependent services use the certificate.
resource "aws_acm_certificate_validation" "this" {
  count = var.create ? 1 :0
  certificate_arn = aws_acm_certificate.this[0].arn
  validation_record_fqdns = [for record in aws_route53_record.validation :record.fqdn]
}
