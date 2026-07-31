# `sqs` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Encrypted work queue and dead-letter queue

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_sqs_queue.dlq`:** Creates a KMS-encrypted task or dead-letter queue.
- **`aws_sqs_queue.tasks`:** Creates a KMS-encrypted task or dead-letter queue.
- **`aws_sqs_queue_redrive_allow_policy.dlq`:** Limits which source queue may redrive messages from the DLQ.
- **`aws_sqs_queue_policy.tasks`:** Denies non-TLS queue access.
- **`aws_sqs_queue_policy.dlq`:** Denies non-TLS queue access.
- **Data `data.aws_iam_policy_document.tasks`:** Builds a structured IAM, resource, trust, or key policy.
- **Data `data.aws_iam_policy_document.dlq`:** Builds a structured IAM, resource, trust, or key policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable queue-name prefix. |
| `kms_key_arn` | `string` | `required` | `false` | Customer-managed KMS key ARN used by both queues. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `queue_url` | Published `queue_url` value. | `aws_sqs_queue.tasks.url` |
| `queue_arn` | Published `queue_arn` value. | `aws_sqs_queue.tasks.arn` |
| `dlq_arn` | Published `dlq_arn` value. | `aws_sqs_queue.dlq.arn` |

## Security and reliability controls

- Customer-managed KMS encryption.
- TLS-only resource policies.
- 14-day DLQ retention.
- Source-restricted redrive.

## Example

```hcl
module "sqs" {
  source = "./modules/sqs"
  name = var.name
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
