# `eventbridge` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Encrypted campaign-expiry scheduling

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_iam_role.scheduler`:** Creates a narrowly trusted service or deployment role.
- **`aws_iam_role_policy.scheduler`:** Grants resource-scoped permissions required by the role.
- **`aws_cloudwatch_event_bus.this`:** Creates the environment event bus.
- **`aws_scheduler_schedule_group.this`:** Groups related EventBridge Scheduler schedules.
- **`aws_scheduler_schedule.campaign_expiry`:** Runs the campaign-expiry task on an encrypted schedule with retries and a DLQ.
- **Data `data.aws_iam_policy_document.scheduler_assume`:** Builds a structured IAM, resource, trust, or key policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names and tags. |
| `queue_arn` | `string` | `required` | `false` | Configuration value for `queue_arn`. |
| `dlq_arn` | `string` | `required` | `false` | Configuration value for `dlq_arn`. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key ARN used for encryption. |
| `schedule_enabled` | `bool` | `true` | `false` | Configuration value for `schedule_enabled`. |
| `schedule_expression` | `string` | `"rate(5 minutes)"` | `false` | Configuration value for `schedule_expression`. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `event_bus_arn` | Published `event_bus_arn` value. | `aws_cloudwatch_event_bus.this.arn` |
| `schedule_arn` | Published `schedule_arn` value. | `aws_scheduler_schedule.campaign_expiry.arn` |

## Security and reliability controls

- Scheduler metadata encrypted by CMK.
- Resource-scoped SQS and KMS permissions.
- Retry and dead-letter handling.

## Example

```hcl
module "eventbridge" {
  source = "./modules/eventbridge"
  name = var.name
  queue_arn = var.queue_arn
  dlq_arn = var.dlq_arn
  kms_key_arn = var.kms_key_arn
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

See [`../../README.md`](../../README.md), [`../../../docs/terraform-module-architecture.md`](../../../docs/terraform-module-architecture.md), and [`../../../docs/CHECKOV_REMEDIATION.md`](../../../docs/CHECKOV_REMEDIATION.md).
