resource "aws_sns_topic" "alerts" {
  name = "${var.name}-alerts"
  tags = var.tags
}
resource "aws_sns_topic_subscription" "email" {
  count = var.sns_email == "" ? 0 :1
  topic_arn = aws_sns_topic.alerts.arn
  protocol = "email"
  endpoint = var.sns_email
}
resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  alarm_name = "${var.name}-alb-5xx"
  namespace = "AWS/ApplicationELB"
  metric_name = "HTTPCode_ELB_5XX_Count"
  statistic = "Sum"
  period = 300
  evaluation_periods = 1
  threshold = 5
  comparison_operator = "GreaterThanOrEqualToThreshold"
  dimensions = {LoadBalancer = var.alb_arn_suffix}
  alarm_actions = [aws_sns_topic.alerts.arn]
  tags = var.tags
}
resource "aws_cloudwatch_metric_alarm" "ecs_cpu" {
  alarm_name = "${var.name}-ecs-cpu"
  namespace = "AWS/ECS"
  metric_name = "CPUUtilization"
  statistic = "Average"
  period = 300
  evaluation_periods = 2
  threshold = 80
  comparison_operator = "GreaterThanThreshold"
  dimensions = {ClusterName = var.cluster_name,ServiceName = var.service_name}
  alarm_actions = [aws_sns_topic.alerts.arn]
  tags = var.tags
}
