# `cloudwatch` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - Operational alerting

Creates the alert topic and baseline ALB/ECS alarms used to detect elevated errors or resource pressure.

## What this module does

- **Creates `aws_sns_topic.alerts`:** Creates the notification fan-out channel used by monitoring alarms.
- **Creates `aws_sns_topic_subscription.email`:** Delivers SNS alerts to the configured recipient endpoint.
- **Creates `aws_cloudwatch_metric_alarm.alb_5xx`:** Raises an operational alert when a service metric crosses its defined threshold.
- **Creates `aws_cloudwatch_metric_alarm.ecs_cpu`:** Raises an operational alert when a service metric crosses its defined threshold.

## Execution flow

1. The root stack supplies the inputs listed below.
2. Terraform resolves data sources and derived local values.
3. Resources are created with the inline security and lifecycle controls in `main.tf`.
4. Values in `outputs.tf` are returned to the root stack or deployment scripts.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names, logs, tags, and service identifiers. |
| `alb_arn_suffix` | `string` | `required` | `false` | ALB ARN suffix used by CloudWatch dimensions. |
| `cluster_name` | `string` | `required` | `false` | Name of the ECS cluster used to construct service and autoscaling identifiers. |
| `service_name` | `string` | `required` | `false` | Name of the ECS service used by deployment, autoscaling, and monitoring commands. |
| `sns_email` | `string` | `required` | `false` | Alarm notification email subscribed to the SNS topic. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags applied to supported resources. |

## Outputs

This module does not publish outputs.

## Example

```hcl
module "cloudwatch" {
  source = "./modules/cloudwatch"
  name = var.name
  alb_arn_suffix = var.alb_arn_suffix
  cluster_name = var.cluster_name
  service_name = var.service_name
  sns_email = var.sns_email
}
```

> The root `terraform/main.tf` contains the authoritative production composition. The example above shows the module interface, not a complete standalone deployment.

## Security and reliability notes

- Review every input before production use; defaults are conveniences, not substitutes for environment-specific risk review.
- Keep secret values in AWS Secrets Manager or protected CI/CD secrets. Do not place credentials in `.tfvars` committed to Git.
- Run `terraform fmt`, `terraform validate`, TFLint, Checkov, and the Go contract tests before applying changes.
- Inspect the plan for replacement, deletion, public exposure, IAM expansion, encryption changes, and cross-account effects.

## Files

- `main.tf` - resources and service configuration.
- `variables.tf` - input contract, validation, and defaults.
- `outputs.tf` - values exposed to callers when present.

## Validation

```bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
tflint --recursive
checkov -d .
```

See [`../../README.md`](../../README.md) for environment deployment and [`../../../docs/terraform-module-architecture.md`](../../../docs/terraform-module-architecture.md) for the complete architecture.
