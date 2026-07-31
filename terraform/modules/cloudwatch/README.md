# `cloudwatch` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Encrypted operational alerting

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_sns_topic.alerts`:** Creates an encrypted notification or alarm topic.
- **`aws_sns_topic_policy.alerts`:** Restricts SNS administration, publication, and transport security.
- **`aws_sns_topic_subscription.email`:** Optionally delivers alarm notifications to an email endpoint.
- **`aws_cloudwatch_metric_alarm.alb_5xx`:** Raises an operational alarm when a service metric crosses its threshold.
- **`aws_cloudwatch_metric_alarm.target_5xx`:** Raises an operational alarm when a service metric crosses its threshold.
- **`aws_cloudwatch_metric_alarm.unhealthy_targets`:** Raises an operational alarm when a service metric crosses its threshold.
- **`aws_cloudwatch_metric_alarm.target_latency`:** Raises an operational alarm when a service metric crosses its threshold.
- **`aws_cloudwatch_metric_alarm.ecs_cpu`:** Raises an operational alarm when a service metric crosses its threshold.
- **`aws_cloudwatch_metric_alarm.ecs_memory`:** Raises an operational alarm when a service metric crosses its threshold.
- **`aws_cloudwatch_metric_alarm.queue_backlog`:** Raises an operational alarm when a service metric crosses its threshold.
- **`aws_cloudwatch_metric_alarm.queue_age`:** Raises an operational alarm when a service metric crosses its threshold.
- **`aws_cloudwatch_metric_alarm.dlq_messages`:** Raises an operational alarm when a service metric crosses its threshold.
- **`aws_cloudwatch_metric_alarm.rds_cpu`:** Raises an operational alarm when a service metric crosses its threshold.
- **`aws_cloudwatch_metric_alarm.rds_free_storage`:** Raises an operational alarm when a service metric crosses its threshold.
- **`aws_cloudwatch_metric_alarm.redis_cpu`:** Raises an operational alarm when a service metric crosses its threshold.
- **`aws_cloudwatch_metric_alarm.redis_memory`:** Raises an operational alarm when a service metric crosses its threshold.
- **`aws_cloudwatch_metric_alarm.redis_evictions`:** Raises an operational alarm when a service metric crosses its threshold.
- **`aws_cloudwatch_metric_alarm.cloudfront_5xx`:** Raises an operational alarm when a service metric crosses its threshold.
- **`aws_cloudwatch_dashboard.service`:** Creates and manages `aws_cloudwatch_dashboard` for this module.
- **Data `data.aws_caller_identity.current`:** Reads the active AWS account for account-scoped ARNs and policies.
- **Data `data.aws_partition.current`:** Keeps generated ARNs compatible with the active AWS partition.
- **Data `data.aws_region.current`:** Reads the provider region for service principals and encryption contexts.
- **Data `data.aws_iam_policy_document.alerts`:** Builds a structured IAM, resource, trust, or key policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable prefix for alarms, the dashboard, and the SNS topic. |
| `alb_arn_suffix` | `string` | `required` | `false` | Application Load Balancer ARN suffix used by CloudWatch dimensions. |
| `target_group_arn_suffix` | `string` | `required` | `false` | ALB target-group ARN suffix used by health and latency alarms. |
| `cluster_name` | `string` | `required` | `false` | ECS cluster name. |
| `service_names` | `set(string)` | `required` | `false` | ECS service names monitored for CPU and memory pressure. |
| `db_identifier` | `string` | `required` | `false` | RDS database identifier. |
| `redis_replication_group_id` | `string` | `required` | `false` | ElastiCache replication-group identifier. |
| `queue_name` | `string` | `required` | `false` | Application SQS source queue name. |
| `dlq_name` | `string` | `required` | `false` | Application SQS dead-letter queue name. |
| `cloudfront_distribution_id` | `string` | `required` | `false` | CloudFront distribution identifier. |
| `sns_email` | `string` | `""` | `false` | Optional email endpoint subscribed to the alarm topic. Confirmation is required by AWS. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key used to encrypt the alarm SNS topic. |
| `account_root_arn` | `string` | `required` | `false` | Owning account root ARN used by the explicit SNS administration policy. |
| `thresholds` | `object({` | `{}` | `false` | Operational thresholds. Values are intentionally configurable because traffic and instance sizes differ by environment. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `alarm_topic_arn` | Encrypted SNS topic receiving alarm and recovery notifications. | `aws_sns_topic.alerts.arn` |
| `dashboard_name` | CloudWatch service dashboard name. | `aws_cloudwatch_dashboard.service.dashboard_name` |

## Security and reliability controls

- KMS-encrypted alert topic.
- TLS-only SNS policy.
- ALB and ECS health alarms.

## Example

```hcl
module "cloudwatch" {
  source = "./modules/cloudwatch"
  name = var.name
  alb_arn_suffix = var.alb_arn_suffix
  target_group_arn_suffix = var.target_group_arn_suffix
  cluster_name = var.cluster_name
  service_names = var.service_names
  db_identifier = var.db_identifier
  redis_replication_group_id = var.redis_replication_group_id
  queue_name = var.queue_name
  dlq_name = var.dlq_name
  cloudfront_distribution_id = var.cloudfront_distribution_id
  kms_key_arn = var.kms_key_arn
  account_root_arn = var.account_root_arn
}
```

> The example shows the module contract only. Use `terraform/main.tf` for the complete dependency graph and production wiring.

## Validation

```bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
tflint --recursive
checkov -d .
python scripts/validate_security_remediation.py
```

See [`../../README.md`](../../README.md), [`../../../docs/terraform-module-architecture.md`](../../../docs/terraform-module-architecture.md), [`../../../docs/TERRAFORM_MODULE_DEEP_AUDIT.md`](../../../docs/TERRAFORM_MODULE_DEEP_AUDIT.md), and [`../../../docs/CHECKOV_REMEDIATION.md`](../../../docs/CHECKOV_REMEDIATION.md).
