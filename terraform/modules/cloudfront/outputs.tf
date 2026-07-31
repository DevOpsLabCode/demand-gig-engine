# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes reusable values produced by the cloudfront Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Output `distribution_id`: Identifier of the distribution resource consumed by this module.
output "distribution_id" {
  value = aws_cloudfront_distribution.this.id
}
# Output `domain_name`: Fully qualified DNS name exposed by the service.
output "domain_name" {
  value = aws_cloudfront_distribution.this.domain_name
}
# Output `hosted_zone_id`: Route 53 hosted-zone ID in which DNS records are created.
output "hosted_zone_id" {
  value = aws_cloudfront_distribution.this.hosted_zone_id
}
