# `xray` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Distributed tracing resources

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_xray_sampling_rule.this`:** Creates and manages `aws_xray_sampling_rule` for this module.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Unique X-Ray sampling-rule name. |
| `priority` | `number` | `9000` | `false` | Rule priority; lower numbers are evaluated first. |
| `reservoir_size` | `number` | `1` | `false` | Guaranteed traces sampled each second before fixed-rate sampling. |
| `fixed_rate` | `number` | `0.05` | `false` | Sampling probability after the reservoir is exhausted. |
| `url_path` | `string` | `"*"` | `false` | URL path pattern matched by the rule. |
| `host` | `string` | `"*"` | `false` | Host pattern matched by the rule. |
| `http_method` | `string` | `"*"` | `false` | HTTP method pattern matched by the rule. |
| `service_type` | `string` | `"*"` | `false` | X-Ray service type pattern matched by the rule. |
| `service_name` | `string` | `"*"` | `false` | X-Ray service name pattern matched by the rule. |
| `resource_arn` | `string` | `"*"` | `false` | Resource ARN pattern matched by the rule. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `sampling_rule_arn` | ARN of the X-Ray sampling rule. | `aws_xray_sampling_rule.this.arn` |
| `sampling_rule_name` | Name of the X-Ray sampling rule. | `aws_xray_sampling_rule.this.rule_name` |

## Security and reliability controls

- Resources use the root stack's encryption, network, logging, tagging, and least-privilege conventions where supported.
- Review plans for public exposure, IAM expansion, encryption changes, replacement, and deletion before applying.

## Example

```hcl
module "xray" {
  source = "./modules/xray"
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

See [`../../README.md`](../../README.md), [`../../../docs/terraform-module-architecture.md`](../../../docs/terraform-module-architecture.md), [`../../../docs/TERRAFORM_MODULE_DEEP_AUDIT.md`](../../../docs/TERRAFORM_MODULE_DEEP_AUDIT.md), and [`../../../docs/CHECKOV_REMEDIATION.md`](../../../docs/CHECKOV_REMEDIATION.md).
