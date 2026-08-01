# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates encrypted alert delivery, a service dashboard, and alarms spanning edge, compute, queue, database, and cache health.

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
data "aws_region" "current" {}

resource "aws_sns_topic" "alerts" {
  name              = "${var.name}-alerts"
  kms_master_key_id = var.kms_key_arn
  tags              = var.tags
}

# Deny message publication and topic administration over insecure transport.
data "aws_iam_policy_document" "alerts" {
  statement {
    sid       = "AllowCloudWatchAlarmPublish"
    effect    = "Allow"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.alerts.arn]

    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:${data.aws_partition.current.partition}:cloudwatch:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:alarm:${var.name}-*"]
    }
  }

  statement {
    sid       = "AllowAccountAdministration"
    effect    = "Allow"
    actions   = ["sns:GetTopicAttributes", "sns:SetTopicAttributes", "sns:Subscribe", "sns:Publish"]
    resources = [aws_sns_topic.alerts.arn]

    principals {
      type        = "AWS"
      identifiers = [var.account_root_arn]
    }
  }

  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"
    # SNS topic resource policies accept only the documented topic actions;
    # the wildcard action is rejected by SetTopicAttributes.
    actions = [
      "sns:AddPermission",
      "sns:DeleteTopic",
      "sns:GetDataProtectionPolicy",
      "sns:GetTopicAttributes",
      "sns:ListSubscriptionsByTopic",
      "sns:ListTagsForResource",
      "sns:Publish",
      "sns:PutDataProtectionPolicy",
      "sns:RemovePermission",
      "sns:SetTopicAttributes",
      "sns:Subscribe",
    ]
    resources = [aws_sns_topic.alerts.arn]

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_sns_topic_policy" "alerts" {
  arn    = aws_sns_topic.alerts.arn
  policy = data.aws_iam_policy_document.alerts.json
}

resource "aws_sns_topic_subscription" "email" {
  count = var.sns_email == "" ? 0 : 1

  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.sns_email
}

locals {
  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  alarm_name          = "${var.name}-alb-5xx"
  alarm_description   = "ALB-generated 5xx errors indicate load-balancer or target-connectivity failures."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_ELB_5XX_Count"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = var.thresholds.alb_5xx_count
  comparison_operator = "GreaterThanOrEqualToThreshold"
  dimensions          = { LoadBalancer = var.alb_arn_suffix }
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
  treat_missing_data  = "notBreaching"
  tags                = var.tags
}

resource "aws_cloudwatch_metric_alarm" "target_5xx" {
  alarm_name          = "${var.name}-target-5xx"
  alarm_description   = "Application targets are returning elevated 5xx responses."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_Target_5XX_Count"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = var.thresholds.target_5xx_count
  comparison_operator = "GreaterThanOrEqualToThreshold"
  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.target_group_arn_suffix
  }
  alarm_actions      = local.alarm_actions
  ok_actions         = local.alarm_actions
  treat_missing_data = "notBreaching"
  tags               = var.tags
}

resource "aws_cloudwatch_metric_alarm" "unhealthy_targets" {
  alarm_name          = "${var.name}-unhealthy-targets"
  alarm_description   = "One or more API targets are unhealthy."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.target_group_arn_suffix
  }
  alarm_actions      = local.alarm_actions
  ok_actions         = local.alarm_actions
  treat_missing_data = "breaching"
  tags               = var.tags
}

resource "aws_cloudwatch_metric_alarm" "target_latency" {
  alarm_name          = "${var.name}-target-latency-p95"
  alarm_description   = "API p95 target response time is elevated."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "TargetResponseTime"
  extended_statistic  = "p95"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = var.thresholds.target_response_time_p95
  comparison_operator = "GreaterThanThreshold"
  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.target_group_arn_suffix
  }
  alarm_actions      = local.alarm_actions
  ok_actions         = local.alarm_actions
  treat_missing_data = "notBreaching"
  tags               = var.tags
}

resource "aws_cloudwatch_metric_alarm" "ecs_cpu" {
  for_each            = var.service_names
  alarm_name          = "${var.name}-${each.key}-ecs-cpu"
  alarm_description   = "ECS service ${each.value} CPU utilization is persistently high."
  namespace           = "AWS/ECS"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = var.thresholds.ecs_cpu_percent
  comparison_operator = "GreaterThanThreshold"
  dimensions          = { ClusterName = var.cluster_name, ServiceName = each.value }
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
  treat_missing_data  = "notBreaching"
  tags                = var.tags
}

resource "aws_cloudwatch_metric_alarm" "ecs_memory" {
  for_each            = var.service_names
  alarm_name          = "${var.name}-${each.key}-ecs-memory"
  alarm_description   = "ECS service ${each.value} memory utilization is persistently high."
  namespace           = "AWS/ECS"
  metric_name         = "MemoryUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = var.thresholds.ecs_memory_percent
  comparison_operator = "GreaterThanThreshold"
  dimensions          = { ClusterName = var.cluster_name, ServiceName = each.value }
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
  treat_missing_data  = "notBreaching"
  tags                = var.tags
}

resource "aws_cloudwatch_metric_alarm" "queue_backlog" {
  alarm_name          = "${var.name}-queue-backlog"
  alarm_description   = "The asynchronous work queue contains an elevated number of visible messages."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = var.thresholds.queue_visible_messages
  comparison_operator = "GreaterThanThreshold"
  dimensions          = { QueueName = var.queue_name }
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
  treat_missing_data  = "notBreaching"
  tags                = var.tags
}

resource "aws_cloudwatch_metric_alarm" "queue_age" {
  alarm_name          = "${var.name}-queue-oldest-message"
  alarm_description   = "The oldest queued job is not being processed within the expected window."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateAgeOfOldestMessage"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = var.thresholds.queue_oldest_message_secs
  comparison_operator = "GreaterThanThreshold"
  dimensions          = { QueueName = var.queue_name }
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
  treat_missing_data  = "notBreaching"
  tags                = var.tags
}

resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "${var.name}-dlq-messages"
  alarm_description   = "At least one message has exhausted retries and entered the dead-letter queue."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  dimensions          = { QueueName = var.dlq_name }
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
  treat_missing_data  = "notBreaching"
  tags                = var.tags
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${var.name}-rds-cpu"
  alarm_description   = "Database CPU utilization is persistently high."
  namespace           = "AWS/RDS"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 3
  datapoints_to_alarm = 2
  threshold           = var.thresholds.rds_cpu_percent
  comparison_operator = "GreaterThanThreshold"
  dimensions          = { DBInstanceIdentifier = var.db_identifier }
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
  treat_missing_data  = "notBreaching"
  tags                = var.tags
}

resource "aws_cloudwatch_metric_alarm" "rds_free_storage" {
  alarm_name          = "${var.name}-rds-low-storage"
  alarm_description   = "Database free storage has fallen below the configured safety threshold."
  namespace           = "AWS/RDS"
  metric_name         = "FreeStorageSpace"
  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = var.thresholds.rds_free_storage_bytes
  comparison_operator = "LessThanThreshold"
  dimensions          = { DBInstanceIdentifier = var.db_identifier }
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
  treat_missing_data  = "breaching"
  tags                = var.tags
}

resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name          = "${var.name}-redis-cpu"
  alarm_description   = "Redis engine CPU utilization is persistently high."
  namespace           = "AWS/ElastiCache"
  metric_name         = "EngineCPUUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 3
  datapoints_to_alarm = 2
  threshold           = var.thresholds.redis_cpu_percent
  comparison_operator = "GreaterThanThreshold"
  dimensions          = { ReplicationGroupId = var.redis_replication_group_id }
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
  treat_missing_data  = "notBreaching"
  tags                = var.tags
}

resource "aws_cloudwatch_metric_alarm" "redis_memory" {
  alarm_name          = "${var.name}-redis-memory"
  alarm_description   = "Redis database memory usage is persistently high."
  namespace           = "AWS/ElastiCache"
  metric_name         = "DatabaseMemoryUsagePercentage"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 3
  datapoints_to_alarm = 2
  threshold           = var.thresholds.redis_memory_percent
  comparison_operator = "GreaterThanThreshold"
  dimensions          = { ReplicationGroupId = var.redis_replication_group_id }
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
  treat_missing_data  = "notBreaching"
  tags                = var.tags
}

resource "aws_cloudwatch_metric_alarm" "redis_evictions" {
  alarm_name          = "${var.name}-redis-evictions"
  alarm_description   = "Redis has evicted one or more keys because of memory pressure."
  namespace           = "AWS/ElastiCache"
  metric_name         = "Evictions"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  dimensions          = { ReplicationGroupId = var.redis_replication_group_id }
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
  treat_missing_data  = "notBreaching"
  tags                = var.tags
}

resource "aws_cloudwatch_metric_alarm" "cloudfront_5xx" {
  alarm_name          = "${var.name}-cloudfront-5xx-rate"
  alarm_description   = "CloudFront viewer requests have an elevated 5xx error percentage."
  namespace           = "AWS/CloudFront"
  metric_name         = "5xxErrorRate"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = var.thresholds.cloudfront_5xx_percent
  comparison_operator = "GreaterThanThreshold"
  dimensions = {
    DistributionId = var.cloudfront_distribution_id
    Region         = "Global"
  }
  alarm_actions      = local.alarm_actions
  ok_actions         = local.alarm_actions
  treat_missing_data = "notBreaching"
  tags               = var.tags
}

resource "aws_cloudwatch_dashboard" "service" {
  dashboard_name = var.name
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Edge and API health"
          region = data.aws_region.current.region
          metrics = [
            ["AWS/ApplicationELB", "HTTPCode_ELB_5XX_Count", "LoadBalancer", var.alb_arn_suffix],
            [".", "HTTPCode_Target_5XX_Count", ".", ".", "TargetGroup", var.target_group_arn_suffix],
            [".", "TargetResponseTime", ".", ".", ".", "."],
          ]
          period = 300
          stat   = "Average"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "ECS service utilization"
          region = data.aws_region.current.region
          # Build one metric row per service/metric pair. Terraform flatten()
          # recursively flattened the rows into strings, while CloudWatch
          # requires metrics to remain an array of string arrays.
          metrics = [
            for service_metric in setproduct(
              sort(keys(var.service_names)),
              ["CPUUtilization", "MemoryUtilization"],
              ) : [
              "AWS/ECS",
              service_metric[1],
              "ClusterName",
              var.cluster_name,
              "ServiceName",
              var.service_names[service_metric[0]],
            ]
          ]
          period = 300
          stat   = "Average"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "Async queue health"
          region = data.aws_region.current.region
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", var.queue_name],
            [".", "ApproximateAgeOfOldestMessage", ".", "."],
            [".", "ApproximateNumberOfMessagesVisible", ".", var.dlq_name],
          ]
          period = 300
          stat   = "Maximum"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "Database and cache health"
          region = data.aws_region.current.region
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", var.db_identifier],
            [".", "FreeStorageSpace", ".", "."],
            ["AWS/ElastiCache", "EngineCPUUtilization", "ReplicationGroupId", var.redis_replication_group_id],
            [".", "DatabaseMemoryUsagePercentage", ".", "."],
          ]
          period = 300
          stat   = "Average"
        }
      },
    ]
  })
}
