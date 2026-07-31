# `waf` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Managed web firewall and encrypted request logging

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_wafv2_web_acl.this`:** Applies AWS managed rules and per-IP rate limiting at the edge.
- **`aws_kms_key.logging`:** Creates a rotating customer-managed encryption key with a constrained key policy.
- **`aws_cloudwatch_log_group.this`:** Stores encrypted logs with a policy-enforced retention period.
- **`aws_wafv2_web_acl_logging_configuration.this`:** Sends redacted full-request WAF logs to encrypted CloudWatch Logs.
- **Data `data.aws_caller_identity.current`:** Reads the active AWS account for account-scoped ARNs and policies.
- **Data `data.aws_partition.current`:** Keeps generated ARNs compatible with the active AWS partition.
- **Data `data.aws_region.current`:** Reads the provider region for service principals and encryption contexts.
- **Data `data.aws_iam_policy_document.logging_kms`:** Builds a structured IAM, resource, trust, or key policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Name prefix for the Web ACL and its encrypted log group. |
| `scope` | `string` | `"CLOUDFRONT"` | `false` | WAF scope. CloudFront requires CLOUDFRONT and an us-east-1 provider. |
| `rate_limit` | `number` | `2000` | `false` | Maximum requests per five-minute evaluation window per source IP. |
| `log_retention_days` | `number` | `365` | `false` | CloudWatch retention for full WAF request logs. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `arn` | Published `arn` value. | `aws_wafv2_web_acl.this.arn` |
| `id` | Published `id` value. | `aws_wafv2_web_acl.this.id` |

## Security and reliability controls

- AWS managed rule groups.
- Per-IP rate limiting.
- KMS-encrypted 365-day logs.
- Authorization and Cookie fields redacted.

## Example

```hcl
module "waf" {
  source = "./modules/waf"
  name = var.name
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
