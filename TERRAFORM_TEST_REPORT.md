# Terraform framework deep validation report

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)


**Project:** Demand Gig Engine  
**Validation date:** July 30, 2026  
**Framework:** `terraform/` AWS development and production stacks

## Executive result

The framework passed every executable offline test available in this environment after a deep source, security, orchestration, and deployment-contract review. The final package contains **24 reusable AWS modules**, **76 Terraform files**, **29 root module instances**, and **27 Go tests**. All Go tests passed with the race detector, including a mocked end-to-end deployment that exercises remote-state bootstrap, image publication, zero-capacity provisioning, one-off migrations, service scale-up, static publication, and CloudFront invalidation.

Native Terraform provider initialization, provider-schema validation, TFLint, Checkov, Docker builds, and an AWS plan/apply could not be executed locally because this sandbox does not provide those binaries, blocks external package downloads, and has no AWS credentials. These checks are wired into `.github/workflows/terraform.yml` and remain required before a real environment deployment.

## Executed checks

| Check | Result | Evidence |
|---|---|---|
| Archive/source integrity | PASS | Working tree extracted and inspected successfully |
| Terraform structural scan | PASS | 76 `.tf` files; balanced blocks, strings, and expressions |
| Root/module interface contracts | PASS | 29 root module instances matched declared module variables and outputs |
| Same-line HCL object separator regression | PASS | No compressed object assignments without comma/newline separators |
| Required module inventory | PASS | 24 distinct service/responsibility modules present |
| Dev/prod `.tfvars` contract | PASS | Real environment values and required keys present |
| Production safety contract | PASS | Multi-AZ, deletion protection, API redundancy, Redis replicas, NAT-per-AZ |
| Go test suite | PASS | 27 tests passed |
| Go race detector | PASS | `go test -race -count=1 -v ./...` |
| Go static analysis | PASS | `go vet ./...` |
| Mock state bootstrap | PASS | Idempotent secure S3 backend, versioning, encryption, public block, TLS policy |
| Mock deployment orchestration | PASS | Build/push, zero capacity, migration task, scale-up, S3 sync, CloudFront invalidation |
| Shell syntax | PASS | Application, security, bootstrap, validate, and deployment scripts |
| Python compilation | PASS | Backend and repository scripts compiled |
| Repository structural validation | PASS | 69 checks, 0 failures |
| GitHub workflow validation | PASS | 5 workflow files and approved action majors |
| TypeScript/TSX parsing | PASS | 13 source files, 0 syntax diagnostics |
| CloudFront Function behavior | PASS | 5 SPA/static routing cases |
| Credential-pattern scan | PASS | 0 AWS/private-key/GitHub/Stripe credential findings |
| VibesMeet contract unit tests | PASS | 2 tests |
| VibesMeet pytest suite | PASS | 41 tests |

## Critical defects found and fixed

1. **Invalid compressed HCL:** generated one-line blocks and object expressions would have failed native Terraform parsing. All 76 Terraform files were normalized into readable blocks, and invalid EventBridge IAM object separators were corrected.
2. **Incorrect certificate region coupling:** one `us-east-1` certificate was being reused for CloudFront and the ALB. The stack now creates a CloudFront viewer certificate in `us-east-1` and a separate ALB-origin certificate in the workload region.
3. **WAF placement:** the Web ACL is attached to CloudFront using the `CLOUDFRONT` scope.
4. **Origin bypass:** ALB ingress is restricted to the AWS-managed CloudFront origin-facing prefix list.
5. **Origin TLS:** `origin.<domain>` resolves to the ALB, uses its regional certificate, and is used as the CloudFront HTTPS origin.
6. **SPA/API error corruption:** global CloudFront 403/404 rewrites were removed. A CloudFront Function rewrites extensionless frontend paths only on the S3 behavior.
7. **Production frontend API failure:** frontend production builds previously defaulted to `localhost`. They now default to same-origin `/api`, while Docker Compose injects the local absolute API URL at build time.
8. **Docker Compose port mismatch:** the unprivileged Nginx image listens on `8080`; Compose now maps `5173:8080`.
9. **Frontend build permissions:** the Node build stage now owns `/app` before running npm and Vite as a non-root user.
10. **Autoscaling identifier:** the ECS Application Auto Scaling resource ID now uses `service/<cluster-name>/<service-name>`.
11. **Migration health-check deadlock:** database migrations now use a dedicated zero-capacity task definition with no web health check or X-Ray sidecar.
12. **ECS Exec authorization:** task roles now include the required `ssmmessages` channel permissions because services enable ECS Exec.
13. **IPv4 ALB origin DNS:** the Route 53 module supports optional AAAA aliases, and the IPv4-only ALB origin explicitly disables AAAA publication.
14. **Async worker gap:** a Django SQS worker command processes scheduled campaign-expiry events with retry-safe deletion behavior.
15. **EventBridge scheduler contract:** Scheduler sends the typed expiry message to SQS with retries and a DLQ.
16. **Media storage:** private KMS-encrypted S3 media storage is integrated through `django-storages` and task-role permissions.
17. **Tracing:** ECS includes an X-Ray daemon sidecar and Django SDK integration; the migration task disables tracing.
18. **Static caching:** immutable assets receive one-year cache headers; `index.html` is published with no-cache headers before CloudFront invalidation.
19. **Non-interactive provider secrets:** `PROVIDER_CREDENTIALS_FILE` can populate the generated Secrets Manager vault before API/worker scale-up without committing credentials.
20. **Outdated GitHub actions:** Terraform setup and TFLint setup were moved to Node-24-compatible action majors.

## Architecture contracts verified

- Route 53 → CloudFront + WAF → private S3 or CloudFront-only ALB.
- Public, private application, and private database subnet tiers.
- ECS Fargate API, worker, and migration task definitions.
- RDS PostgreSQL Multi-AZ option with RDS Proxy and TLS.
- ElastiCache Redis with transit/at-rest encryption and failover replicas.
- SQS work queue and DLQ, EventBridge Scheduler, and SES identity/DKIM.
- Secrets Manager and customer-managed KMS key integration.
- CloudWatch alarms, CloudTrail, GuardDuty, X-Ray, and AWS Backup.
- ECR immutable repositories and GitHub Actions OIDC without static AWS keys.
- Native S3 state lockfiles with isolated development and production state keys.

## Native checks deferred to GitHub/AWS

| Check | Why not run locally | Where it runs |
|---|---|---|
| `terraform fmt` | Terraform executable unavailable | Terraform GitHub workflow and deploy script |
| `terraform init -backend=false` | Terraform executable/provider downloads unavailable | Terraform GitHub workflow |
| `terraform validate` | Terraform executable/provider schemas unavailable | Terraform GitHub workflow |
| TFLint | Binary/plugin downloads unavailable | Terraform GitHub workflow |
| Checkov | Package unavailable from sandbox mirror | Terraform and security workflows |
| Docker backend/frontend builds | Docker CLI/daemon unavailable | Deployment runner or developer machine |
| AWS development plan | No AWS role/credentials | Same-repository PR workflow using `AWS_TERRAFORM_ROLE_ARN` |
| AWS apply and smoke test | No AWS account/credentials/domain/provider apps | Manual protected environment deployment |
| Complete Django/Allauth suite | Sandbox mirror has no Django distributions | Application GitHub matrix |
| Complete Vite build | Sandbox npm mirror lacks required packages | Frontend GitHub job and Docker build |

## Reproduce locally

```bash
./terraform/scripts/validate.sh

cd terraform/tests
go test -race -count=1 -v ./...
go vet ./...
```

For a non-interactive development deployment after AWS authentication:

```bash
PROVIDER_CREDENTIALS_FILE=/secure/path/provider-credentials.json \
  ./terraform/scripts/deploy.sh dev
```

Production uses the same command with `prod`, a protected AWS role/environment, real DNS values, and production provider credentials.

## Documentation-only verification - July 31, 2026

All 76 Terraform files received inline explanations for resources, modules, variables, outputs, policies, lifecycle rules, and nested configuration blocks. All 24 reusable module READMEs were rebuilt from the modules' actual interfaces and resources. A comment-stripped comparison confirmed that the Terraform executable content remained equivalent to the validated pre-documentation baseline. The complete evidence is in [`validation/documentation-enhancement-2026-07-31/`](validation/documentation-enhancement-2026-07-31/).
