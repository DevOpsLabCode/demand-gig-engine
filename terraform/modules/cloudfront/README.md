# `cloudfront` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose — Secure global content and API delivery

This module is consumed by the production composition in `terraform/main.tf`. The Terraform source remains authoritative; this README is generated from the current module interface.

## Resources and data flow

- **`aws_cloudfront_origin_access_control.this`:** Allows signed CloudFront access to the private S3 origin.
- **`aws_cloudfront_function.spa_rewrite`:** Rewrites extensionless single-page application routes to the application shell.
- **`aws_cloudfront_function.true_client_ip`:** Rewrites extensionless single-page application routes to the application shell.
- **`aws_cloudfront_response_headers_policy.security`:** Adds browser security headers to CloudFront responses.
- **`aws_cloudfront_distribution.this`:** Delivers the React frontend and dynamic API routes through HTTPS and WAF.
- **`aws_s3_bucket_policy.this`:** Applies service-delivery permissions and denies insecure transport.
- **Data `data.aws_iam_policy_document.bucket`:** Builds a structured IAM, resource, trust, or key policy.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable distribution, function, OAC, and policy name prefix. |
| `bucket_id` | `string` | `required` | `false` | Private static-site S3 bucket ID whose policy is managed by this module. |
| `bucket_arn` | `string` | `required` | `false` | Private static-site S3 bucket ARN. |
| `bucket_domain_name` | `string` | `required` | `false` | Regional S3 hostname used by the private origin. |
| `alb_domain_name` | `string` | `required` | `false` | ALB origin hostname; custom-domain HTTPS mode requires a matching certificate. |
| `origin_verify_header_value` | `string` | `required` | `true` | High-entropy shared secret sent only to the ALB origin and matched by ALB listener rules to prevent direct origin bypass. |
| `use_https_origin` | `bool` | `false` | `false` | Use TLS from CloudFront to the ALB when a custom origin certificate is available. |
| `domain_name` | `string` | `""` | `false` | Optional public alias. Empty uses the default CloudFront domain. |
| `certificate_arn` | `string` | `null` | `false` | Optional us-east-1 ACM certificate ARN used by the public alias. |
| `web_acl_arn` | `string` | `required` | `false` | ARN of the CLOUDFRONT-scope WAF web ACL. |
| `access_log_bucket_domain_name` | `string` | `required` | `false` | S3 bucket domain used for CloudFront standard access logs. |
| `price_class` | `string` | `"PriceClass_100"` | `false` | CloudFront edge-location price class. |
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
  origin_verify_header_value = var.origin_verify_header_value
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

See [`../../README.md`](../../README.md), [`../../../docs/terraform-module-architecture.md`](../../../docs/terraform-module-architecture.md), [`../../../docs/TERRAFORM_MODULE_DEEP_AUDIT.md`](../../../docs/TERRAFORM_MODULE_DEEP_AUDIT.md), and [`../../../docs/CHECKOV_REMEDIATION.md`](../../../docs/CHECKOV_REMEDIATION.md).
