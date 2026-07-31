# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates an X-Ray sampling rule so distributed traces are captured at a controlled rate.
# Reading guide: Each comment explains why the following Terraform block exists.

# Create and manage the aws xray sampling rule resource owned by this file.
resource "aws_xray_sampling_rule" "this" {
  rule_name = var.name
  priority = 10000
  version = 1
  reservoir_size = 1
  fixed_rate = 0.05
  url_path = "*"
  host = "*"
  http_method = "*"
  service_type = "*"
  service_name = "*"
  resource_arn = "*"
}
