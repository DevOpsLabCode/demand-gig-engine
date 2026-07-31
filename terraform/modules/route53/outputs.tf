# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes reusable values produced by the route53 Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Output `fqdn`: Fully qualified DNS record created by the module, or null when DNS creation is disabled.
output "fqdn" {
  value = try(aws_route53_record.ipv4[0].fqdn, null)
}
