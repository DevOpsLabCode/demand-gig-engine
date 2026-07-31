# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates a configurable X-Ray sampling rule while the workload migrates trace export to AWS Distro for OpenTelemetry.

resource "aws_xray_sampling_rule" "this" {
  rule_name      = var.name
  priority       = var.priority
  version        = 1
  reservoir_size = var.reservoir_size
  fixed_rate     = var.fixed_rate
  url_path       = var.url_path
  host           = var.host
  http_method    = var.http_method
  service_type   = var.service_type
  service_name   = var.service_name
  resource_arn   = var.resource_arn
}
