# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates a CloudFront-scoped Web ACL with AWS managed protections, IP rate limiting, logging, and metrics.
# Reading guide: Each comment explains why the following Terraform block exists.

# Create and manage the aws wafv2 web acl resource owned by this file.
resource "aws_wafv2_web_acl" "this" {
  name = var.name
  scope = var.scope
  # Specifies the action used when no more-specific WAF rule matches.
  default_action {
    allow {
    }
  }
  # Enables metrics and sampled-request visibility for this WAF scope.
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name = var.name
    sampled_requests_enabled = true
  }
  # Defines one ordered policy or lifecycle rule.
  rule {
    name = "AWSManagedCommon"
    priority = 10
    override_action {
      none {
      }
    }
    # Apply AWS managed baseline protections for common web exploits and malformed requests.
    statement {
      managed_rule_group_statement {
        name = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }
    # Enables metrics and sampled-request visibility for this WAF scope.
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name = "common"
      sampled_requests_enabled = true
    }
  }
  # Defines one ordered policy or lifecycle rule.
  rule {
    name = "KnownBadInputs"
    priority = 20
    override_action {
      none {
      }
    }
    # Block request patterns AWS identifies as known malicious or high-risk input.
    statement {
      managed_rule_group_statement {
        name = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }
    # Enables metrics and sampled-request visibility for this WAF scope.
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name = "bad-inputs"
      sampled_requests_enabled = true
    }
  }
  # Defines one ordered policy or lifecycle rule.
  rule {
    name = "RateLimit"
    priority = 30
    action {
      block {
      }
    }
    # Rate-limit each source IP to reduce abuse and protect the application origin from request floods.
    statement {
      rate_based_statement {
        limit = var.rate_limit
        aggregate_key_type = "IP"
      }
    }
    # Enables metrics and sampled-request visibility for this WAF scope.
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name = "rate"
      sampled_requests_enabled = true
    }
  }
  tags = var.tags
}
