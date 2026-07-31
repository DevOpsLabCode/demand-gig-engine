# Demand Gig Engine Terraform framework

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)


This directory deploys the AWS production architecture documented in [`../docs/terraform-module-architecture.md`](../docs/terraform-module-architecture.md). It contains 24 reusable service modules, isolated development and production values, secure S3 remote state, Go contract/orchestration tests, GitHub OIDC, and an automated build–migrate–deploy pipeline.

## Structure

```text
terraform/
├── modules/                  # 24 reusable AWS modules
├── envs/
│   ├── dev/terraform.tfvars
│   └── prod/terraform.tfvars
├── global/bootstrap/         # reference state bootstrap stack
├── scripts/
│   ├── bootstrap.sh
│   ├── deploy.sh
│   └── validate.sh
├── tests/                    # Go contract, race, integration, and mock-deploy tests
├── main.tf
├── variables.tf
├── outputs.tf
├── providers.tf
└── versions.tf
```

## Prerequisites

- Terraform 1.13.x or a compatible later 1.x release.
- AWS CLI v2 authenticated to the target account.
- Docker with BuildKit support.
- `jq`, Git, and Go 1.23+ for tests.
- Route 53 hosted-zone ID and domain when `create_dns=true`.
- OAuth/payment/integration credentials supplied through a secure JSON file or entered into the generated Secrets Manager secret.

## Validate

```bash
./terraform/scripts/validate.sh

cd terraform/tests
go test -race -count=1 -v ./...
go vet ./...
```

The integration-tag test additionally invokes native Terraform commands:

```bash
cd terraform/tests
go test -tags=integration -count=1 -v ./...
```

See [`../TERRAFORM_TEST_REPORT.md`](../TERRAFORM_TEST_REPORT.md) for the complete executed and deferred test matrix.

## Deploy without Terraform prompts

```bash
./terraform/scripts/deploy.sh dev
./terraform/scripts/deploy.sh prod
```

The deployment script discovers the account ID, provisions secure S3 state with native lockfiles, builds and publishes both containers, provisions infrastructure at zero application capacity, runs a dedicated database migration task, scales services, publishes React assets to S3 with safe cache headers, and invalidates CloudFront.

External credentials can also be injected without an interactive Secrets Manager step:

```bash
PROVIDER_CREDENTIALS_FILE=/secure/path/provider-credentials.json \
  ./terraform/scripts/deploy.sh dev
```

The JSON object may contain the documented Google, Facebook, Instagram, TikTok, Stripe, Meta, and VibesMeet keys. Never commit this file.

## Configure DNS

Edit the chosen environment's real `.tfvars`:

```hcl
create_dns     = true
domain_name    = "gig.example.com"
hosted_zone_id = "Z1234567890"
```

Terraform requests two DNS-validated certificates:

- A **CloudFront viewer certificate in `us-east-1`** for `gig.example.com`.
- A **regional ALB origin certificate** for `origin.gig.example.com`.

Route 53 points the public name to CloudFront and the origin name to the ALB. The ALB accepts port 80/443 only from AWS's managed CloudFront origin-facing prefix list. Because the ALB is IPv4-only, the origin record publishes only an A alias; the CloudFront viewer record publishes A and AAAA aliases.

## Configure runtime secrets

After the first apply, obtain the provider vault ARN:

```bash
terraform -chdir=terraform output -raw provider_credentials_secret_arn
```

Update the JSON keys for Google, Facebook, Instagram, TikTok, Stripe, Meta, and VibesMeet with AWS Secrets Manager. Terraform creates the schema but intentionally ignores later secret-value changes so rotation is not overwritten.

## GitHub Actions

`.github/workflows/terraform.yml` runs Terraform formatting/normalization, provider initialization without the remote backend, native validation, TFLint, Go race tests, and Checkov. It uses Node-24-compatible `hashicorp/setup-terraform@v4` and `terraform-linters/setup-tflint@v6` actions.

Same-repository pull requests can create a development plan. Manual workflow runs deploy `dev` or `prod` using the protected environment secret `AWS_TERRAFORM_ROLE_ARN` and GitHub OIDC—never permanent AWS access keys.

## Operational notes

- `dev` and `prod` use separate state buckets/keys and are intended for separate AWS accounts.
- If both stacks temporarily share an account, ensure account-global resources such as the GitHub OIDC provider are managed only once.
- WAF is associated with CloudFront, not the ALB.
- API, account, admin, and share paths go to Django; the SPA rewrite function applies only to the S3 behavior.
- The browser defaults to the same-origin `/api` path in AWS. Docker Compose supplies `http://localhost:8000/api` at frontend build time for local development.
- The API, worker, and migration tasks share one reusable ECS module but have distinct task definitions and roles.
- The X-Ray daemon uses the AWS-documented `3.x` public ECR channel; plan a future migration to OpenTelemetry for long-term instrumentation.
