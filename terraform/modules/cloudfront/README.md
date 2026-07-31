# `cloudfront` Terraform module

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)

## Purpose - Global edge delivery

Delivers the private React frontend and routes API paths to the ALB while applying origin access control, security headers, and SPA rewrites.

## What this module does

- **Creates `aws_cloudfront_origin_access_control.this`:** Allows CloudFront to read the private frontend bucket using signed origin requests.
- **Creates `aws_cloudfront_function.spa_rewrite`:** Runs lightweight request-rewrite logic at CloudFront edge locations.
- **Creates `aws_cloudfront_response_headers_policy.security`:** Adds browser security and caching headers to CloudFront responses.
- **Creates `aws_cloudfront_distribution.this`:** Creates the global content-delivery layer for the frontend and API origin.
- **Creates `aws_s3_bucket_policy.this`:** Applies resource-level access controls and transport requirements to the bucket.
- **Reads `aws_iam_policy_document.bucket`:** Build the S3 bucket policy that grants read access only to this CloudFront distribution and denies non-TLS requests.

## Execution flow

1. The root stack supplies the inputs listed below.
2. Terraform resolves data sources and derived local values.
3. Resources are created with the inline security and lifecycle controls in `main.tf`.
4. Values in `outputs.tf` are returned to the root stack or deployment scripts.

## Inputs

| Name | Type | Required/default | Sensitive | Description |
|---|---|---|---|---|
| `name` | `string` | `required` | `false` | Stable name prefix used for resource names, logs, tags, and service identifiers. |
| `bucket_id` | `string` | `required` | `false` | Identifier of the bucket resource consumed by this module. |
| `bucket_arn` | `string` | `required` | `false` | ARN of the S3 bucket protected or consumed by the module. |
| `bucket_domain_name` | `string` | `required` | `false` | Regional bucket hostname passed to CloudFront as its private origin. |
| `alb_domain_name` | `string` | `required` | `false` | Origin hostname used by CloudFront. For HTTPS this must be covered by the ALB certificate. |
| `use_https_origin` | `bool` | `false` | `false` | Use TLS between CloudFront and the ALB. |
| `domain_name` | `string` | `required` | `false` | Fully qualified DNS name exposed by the service. |
| `certificate_arn` | `string` | `null` | `false` | ACM certificate ARN used to terminate TLS. |
| `web_acl_arn` | `string` | `required` | `false` | ARN of the CLOUDFRONT-scope WAF web ACL. |
| `price_class` | `string` | `PriceClass_100` | `false` | CloudFront edge-location price class used to balance reach and cost. |
| `tags` | `map(string)` | `{}` | `false` | Common ownership, environment, cost, and governance tags applied to supported resources. |

## Outputs

| Name | Description | Value source |
|---|---|---|
| `distribution_id` | Identifier of the distribution resource consumed by this module. | `aws_cloudfront_distribution.this.id` |
| `domain_name` | Fully qualified DNS name exposed by the service. | `aws_cloudfront_distribution.this.domain_name` |
| `hosted_zone_id` | Route 53 hosted-zone ID in which DNS records are created. | `aws_cloudfront_distribution.this.hosted_zone_id` |

## Example

```hcl
module "cloudfront" {
  source = "./modules/cloudfront"
  name = var.name
  bucket_id = var.bucket_id
  bucket_arn = var.bucket_arn
  bucket_domain_name = var.bucket_domain_name
  alb_domain_name = var.alb_domain_name
  domain_name = var.domain_name
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
