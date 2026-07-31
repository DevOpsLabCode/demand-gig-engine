# Demand Gig Engine Terraform framework

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)


This directory deploys the AWS production architecture documented in [`../docs/terraform-module-architecture.md`](../docs/terraform-module-architecture.md). It contains 25 reusable service modules, isolated development and production values, secure S3 remote state, Go contract/orchestration tests, GitHub OIDC, and an automated build–migrate–deploy pipeline.

## Structure

```text
terraform/
├── modules/                  # 25 reusable AWS modules
├── envs/
│   ├── dev/terraform.tfvars
│   └── prod/terraform.tfvars
├── global/
│   ├── account/             # one-time OIDC, GuardDuty, and ECR scanning foundation
│   └── bootstrap/           # reference remote-state bootstrap stack
├── scripts/
│   ├── bootstrap-account.sh
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

- Terraform 1.15.8 (the workflow and provider constraints are pinned to the tested 1.15 release line).
- AWS CLI v2 authenticated to the target account.
- Docker with BuildKit support.
- `jq`, Git, and Go 1.23+ for tests.
- Route 53 hosted-zone ID and domain when `create_dns=true`.
- OAuth/payment/integration credentials supplied through a secure JSON file or entered into the generated Secrets Manager secret.


## Security remediation baseline

The framework includes a centralized `access_logs` module, blocking Checkov enforcement, a dependency-free remediation validator, encrypted queue/scheduler/notification paths, 365-day security-log retention, Vault Lock, authenticated Redis, secure subnet defaults, and production-safe RDS/ALB deletion controls. See [`../docs/CHECKOV_REMEDIATION.md`](../docs/CHECKOV_REMEDIATION.md) for the finding-by-finding mapping and justified exceptions.

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

## Bootstrap account-wide controls once

GitHub's IAM OIDC provider and GuardDuty detector are account-level singletons. Apply them once before any environment stack:

```bash
./terraform/scripts/bootstrap-account.sh
terraform -chdir=terraform/global/account init -backend-config=backend.hcl
terraform -chdir=terraform/global/account apply
```

The first apply requires trusted local AWS credentials because GitHub federation does not exist yet.

## Deploy without Terraform prompts

```bash
./terraform/scripts/deploy.sh dev
./terraform/scripts/deploy.sh prod
```

The deployment script discovers the account ID, reconciles KMS-protected S3 state with native lockfiles, builds and publishes immutable container tags, provisions the dedicated migration task and dependencies, runs a backward-compatible database migration while the current services remain online, performs the full rolling service update only after migration succeeds, publishes React assets with safe cache headers, and invalidates CloudFront.

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

Route 53 points the public name to CloudFront and the origin name to the ALB. The ALB accepts port 80/443 only from AWS's managed CloudFront origin-facing prefix list and forwards only requests containing the generated per-environment origin secret. CloudFront deliberately does not forward the viewer `Host` header, so origin TLS validates against `origin.<domain>`. Because the ALB is IPv4-only, the origin record publishes only an A alias; the CloudFront viewer record publishes A and AAAA aliases.

## Configure runtime secrets

After the first apply, obtain the provider vault ARN:

```bash
terraform -chdir=terraform output -raw provider_credentials_secret_arn
```

Update the JSON keys for Google, Facebook, Instagram, TikTok, Stripe, Meta, and VibesMeet with AWS Secrets Manager. Terraform creates the schema but intentionally ignores later secret-value changes so rotation is not overwritten.

## GitHub Actions

`.github/workflows/python-package.yml` runs Terraform formatting/normalization, provider initialization without the remote backend, native validation, TFLint, Go race tests, and Checkov. It uses Node-24-compatible `hashicorp/setup-terraform@v4` and `terraform-linters/setup-tflint@v6` actions.

Pull requests receive offline Terraform formatting, native validation, TFLint, Checkov, module-contract, and Go tests without AWS credentials or remote-state access. After trusted code reaches `main`, the protected `dev` environment can assume `AWS_TERRAFORM_PLAN_ROLE_ARN` for a real development plan. Manual workflow runs use `AWS_TERRAFORM_APPLY_ROLE_ARN`; neither path uses permanent AWS access keys or a broader fallback role.

## Operational notes

- `dev` and `prod` use separate state buckets/keys and are intended for separate AWS accounts. Apply `global/account` once in each account.
- Account-wide OIDC, GuardDuty, and ECR enhanced scanning are never owned by environment state.
- Separate WAF ACLs protect CloudFront and the regional ALB origin.
- API, account, admin, and share paths go to Django; the SPA rewrite function applies only to the S3 behavior.
- The browser defaults to the same-origin `/api` path in AWS. Docker Compose supplies `http://localhost:8000/api` at frontend build time for local development.
- The API, worker, and migration tasks share one reusable ECS module but have distinct task definitions, roles, and SQS/data permissions.
- PostgreSQL/upgrade logs and Redis engine/slow logs are pre-created with customer-managed encryption and one-year retention.
- The X-Ray daemon is pinned to `3.6.6`; the sampling rule is configurable, and the documented long-term path is AWS Distro for OpenTelemetry.
- See [`../docs/TERRAFORM_MODULE_DEEP_AUDIT.md`](../docs/TERRAFORM_MODULE_DEEP_AUDIT.md) for the module-by-module readiness review and remaining organizational prerequisites.
