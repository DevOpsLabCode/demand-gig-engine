# `cloudfront` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Secure global content and API delivery

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_cloudfront_origin_access_control.this`:** Allows signed CloudFront access to the private S3 origin.
- **`aws_cloudfront_function.spa_rewrite`:** Rewrites extensionless single-page application routes to the application shell.
- **`aws_cloudfront_response_headers_policy.security`:** Adds browser security headers to CloudFront responses.
- **`aws_cloudfront_distribution.this`:** Delivers the React frontend and dynamic API routes through HTTPS and WAF.
- **`aws_s3_bucket_policy.this`:** Applies service-delivery permissions and denies insecure transport.
- **Data `data.aws_iam_policy_document.bucket`:** Builds a structured IAM, resource, trust, or key policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names and tags. |
| `bucket_id` | `string` | `required` | `false` | S3 bucket name consumed by this module. |
| `bucket_arn` | `string` | `required` | `false` | S3 bucket ARN consumed by this module. |
| `bucket_domain_name` | `string` | `required` | `false` | Regional S3 endpoint used by CloudFront. |
| `alb_domain_name` | `string` | `required` | `false` | ALB origin hostname; custom-domain HTTPS mode requires a matching certificate. |
| `use_https_origin` | `bool` | `false` | `false` | Use TLS from CloudFront to the ALB when a custom origin certificate is available. |
| `domain_name` | `string` | `""` | `false` | Configuration value for `domain_name`. |
| `certificate_arn` | `string` | `null` | `false` | ACM certificate ARN used for TLS; null enables the documented restricted development path. |
| `web_acl_arn` | `string` | `required` | `false` | ARN of the CLOUDFRONT-scope WAF web ACL. |
| `access_log_bucket_domain_name` | `string` | `required` | `false` | S3 bucket domain used for CloudFront standard access logs. |
| `price_class` | `string` | `"PriceClass_100"` | `false` | Configuration value for `price_class`. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `distribution_id` | Published `distribution_id` value. | `aws_cloudfront_distribution.this.id` |
| `domain_name` | Published `domain_name` value. | `aws_cloudfront_distribution.this.domain_name` |
| `hosted_zone_id` | Published `hosted_zone_id` value. | `aws_cloudfront_distribution.this.hosted_zone_id` |

## Security and reliability controls

- Viewer HTTPS redirection.
- WAF association.
- Standard access logging.
- Private signed S3 origin.

## Example

```hcl
module "cloudfront" {
  source = "./modules/cloudfront"
  name = var.name
  bucket_id = var.bucket_id
  bucket_arn = var.bucket_arn
  bucket_domain_name = var.bucket_domain_name
  alb_domain_name = var.alb_domain_name
  web_acl_arn = var.web_acl_arn
  access_log_bucket_domain_name = var.access_log_bucket_domain_name
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
