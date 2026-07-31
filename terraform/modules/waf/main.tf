resource "aws_wafv2_web_acl" "this" {
  name = var.name
  scope = var.scope
  default_action {
    allow {
    }
  }
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name = var.name
    sampled_requests_enabled = true
  }
  rule {
    name = "AWSManagedCommon"
    priority = 10
    override_action {
      none {
      }
    }
    statement {
      managed_rule_group_statement {
        name = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name = "common"
      sampled_requests_enabled = true
    }
  }
  rule {
    name = "KnownBadInputs"
    priority = 20
    override_action {
      none {
      }
    }
    statement {
      managed_rule_group_statement {
        name = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name = "bad-inputs"
      sampled_requests_enabled = true
    }
  }
  rule {
    name = "RateLimit"
    priority = 30
    action {
      block {
      }
    }
    statement {
      rate_based_statement {
        limit = var.rate_limit
        aggregate_key_type = "IP"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name = "rate"
      sampled_requests_enabled = true
    }
  }
  tags = var.tags
}
