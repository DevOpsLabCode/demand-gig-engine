# Demand Gig Engine Terraform module architecture

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)


This document maps the production AWS diagram to the Terraform implementation under `terraform/`. The framework uses one reusable module per AWS service or infrastructure responsibility, then composes those modules into isolated `dev` and `prod` stacks through environment-specific `.tfvars` and remote-state keys.

## Request and deployment paths

```mermaid
flowchart LR
  User[Web and mobile users] --> R53[Route 53]
  R53 --> CF[CloudFront]
  WAF[AWS WAF<br/>CLOUDFRONT scope] --> CF
  CF --> S3[Private S3<br/>React assets]
  CF --> Origin[origin.example.com]
  Origin --> ALB[Public ALB<br/>CloudFront-only SG]
  ALB --> API[ECS Fargate<br/>Django API]
  API --> Proxy[RDS Proxy]
  Proxy --> DB[(RDS PostgreSQL)]
  API --> Redis[(ElastiCache Redis)]
  API --> Media[Private KMS S3 media]
  API --> SES[Amazon SES]
  Scheduler[EventBridge Scheduler] --> Queue[SQS task queue]
  Queue --> Worker[ECS Fargate worker]
  Worker --> DB
  Secrets[Secrets Manager + KMS] --> API
  Secrets --> Worker
  XRay[X-Ray daemon sidecar] --> XRayService[AWS X-Ray]
  API --> XRay

  GitHub[GitHub Actions OIDC] --> ECR[Amazon ECR]
  GitHub --> Terraform[Terraform plan/deploy]
  ECR --> API
  ECR --> Worker
```

CloudFront routes `/api*`, `/accounts*`, `/admin*`, and `/share*` to Django. All other extensionless paths are rewritten by a CloudFront Function to `/index.html`, so SPA routing does not convert API 404 responses into frontend HTML.

When DNS is enabled, Terraform creates two certificates: the CloudFront viewer certificate in `us-east-1`, and a separate ALB-origin certificate in the workload region for `origin.<domain>`. CloudFront connects to the ALB over HTTPS using that origin hostname. The ALB security group accepts port 80/443 only from the AWS-managed CloudFront origin-facing prefix list, preventing direct internet access to the origin.

## Reusable module inventory

| Module | AWS responsibility | Important controls |
|---|---|---|
| `access_logs` | Central S3 audit-log sink | Private/versioned bucket, TLS-only policy, lifecycle cleanup, ALB/CloudFront/S3 delivery compatibility |
| `networking` | VPC, public/app/database subnets, IGW, NAT, route tables, S3 endpoint | No automatic public IPs; three subnet tiers; encrypted one-year flow logs; NAT per AZ in production |
| `security` | ALB, application, database, and Redis security groups | CloudFront-only ALB ingress; SG-to-SG application access |
| `kms` | Customer-managed encryption key | Rotation; CloudWatch Logs and CloudTrail service conditions |
| `acm` | Reusable DNS-validated TLS certificate | Instantiated separately for the `us-east-1` viewer certificate and regional ALB-origin certificate |
| `waf` | Edge Web ACL | Managed rules, IP rate limiting, encrypted full-request logs, sensitive-header redaction |
| `cloudfront` | CDN, S3 OAC, API routing, SPA rewrite, headers | HTTP/2+3, TLS, WAF, OAC, security headers |
| `route53` | Alias records | A and AAAA records for viewer and ALB-origin names |
| `s3_static` | Private static/media buckets | Public-access block, ownership enforcement, versioning, encryption, TLS-only policy |
| `alb` | Application Load Balancer and target group | Invalid-header dropping, deletion protection, TLS 1.2/1.3 policy, health checks |
| `ecr` | Backend/frontend repositories | Immutable tags, KMS encryption, scan-on-push, lifecycle policy |
| `ecs_cluster` | Fargate cluster and logging | Container Insights and encrypted logs |
| `ecs_service` | API, worker, and migration task definitions/services | Read-only root FS, writable `/tmp`, secret injection, least-privilege roles, circuit breaker, autoscaling, X-Ray sidecar |
| `rds_postgres` | PostgreSQL, RDS Proxy, secrets | Private Multi-AZ option, encryption, PI, enhanced monitoring, TLS proxy |
| `redis` | ElastiCache replication group and runtime secret | Transit/at-rest encryption, generated auth token, TLS URL, replicas and failover |
| `sqs` | Work queue and DLQ | Customer-managed KMS encryption, TLS-only policies, long polling, restricted redrive |
| `eventbridge` | Campaign-expiry schedule | Scheduler IAM role, CMK, retries, DLQ |
| `ses` | Transactional email identity | Route 53 verification, DKIM, custom MAIL FROM, SPF, and DMARC |
| `secrets_manager` | OAuth/payment/integration credential vault | KMS encryption; Terraform ignores later secret rotations |
| `cloudwatch` | Metrics, alarms, dashboard, and SNS | Edge/ALB, API/worker ECS, SQS/DLQ, RDS, Redis, and CloudFront alarms |
| `cloudtrail` | Multi-region audit trail | Log validation, KMS, CloudWatch/SNS, production S3 data events and Insights |
| `guardduty` | Threat-detection prerequisite | Reads the detector owned once by `global/account` |
| `xray` | Sampling policy | Configurable X-Ray sampling with documented ADOT/OpenTelemetry migration |
| `backup` | Database backup policy | Encrypted vault, Vault Lock, cold storage, and 365-day minimum retention |
| `github_oidc` | Workload identity for GitHub | Reads shared provider; exact repository/branch/environment trust; PR trust disabled |

There are 25 module directories. The root stack has 29 module instances because `acm` is used for viewer and origin certificates, `route53` is used for viewer and origin records, `s3_static` is used for static and media buckets, and `ecs_service` is used for API, worker, and migration task definitions.

## Account foundation

`terraform/global/account` owns account/region singleton controls: the GitHub IAM OIDC provider, GuardDuty detector and advanced features, Fargate Runtime Monitoring agent management, and enhanced continuous ECR scanning. Environment stacks read these controls instead of recreating them.

The first apply uses trusted local AWS credentials:

```bash
./terraform/scripts/bootstrap-account.sh
terraform -chdir=terraform/global/account init -backend-config=backend.hcl
terraform -chdir=terraform/global/account apply
```

## Environment isolation

```text
terraform/envs/dev/terraform.tfvars
terraform/envs/dev/backend.hcl       # generated, ignored
terraform/envs/prod/terraform.tfvars
terraform/envs/prod/backend.hcl      # generated, ignored
```

The state bucket name includes environment and AWS account ID, and each environment uses a different state key. The intended organization model is a separate AWS account for development and production. If both stacks temporarily share one account, account-global resources such as the GitHub OIDC provider must be managed only once.

Production defaults enforce:

- Three Availability Zones and one NAT gateway per AZ.
- At least two API tasks and two workers.
- Multi-AZ PostgreSQL with RDS Proxy.
- Redis replicas and automatic failover.
- Deletion protection.
- Seven-year CloudTrail archive retention.
- GuardDuty and scheduled campaign-expiry processing.

## Deployment sequence

`terraform/scripts/deploy.sh <environment>` performs the following non-interactively after AWS credentials are available:

1. Runs native Terraform formatting and validation.
2. Creates or verifies the secure remote-state bucket.
3. Creates KMS and ECR first to break the image/infrastructure dependency cycle.
4. Builds and pushes immutable backend and frontend images.
5. Applies infrastructure with API and worker desired counts set to zero.
6. Runs a dedicated migration task definition that has no web health check.
7. Verifies the migration container exit code.
8. Applies the environment-specific API and worker counts.
9. Extracts the compiled React assets from the frontend image.
10. Publishes immutable assets with one-year cache headers and `index.html` with no-cache headers.
11. Invalidates CloudFront.

AWS credentials, OAuth/provider secrets, and—when custom DNS is enabled—the hosted zone/domain are external trust inputs and cannot be invented safely. Provider credentials may be supplied through `PROVIDER_CREDENTIALS_FILE`; everything after those inputs is automated with `-input=false` and `-auto-approve`.

## Tests and policy gates

The local Go tests verify the module inventory, environment contracts, production safety values, credentials, state bootstrap, deployment order, migration gating, regional certificates, CloudFront-only origin access, SPA/API routing, Docker/Compose contracts, same-origin frontend behavior, KMS/TLS storage, tracing, ECS Exec IAM, IPv4 origin DNS, autoscaling identifiers, static cache controls, secret injection, and workflow commands. Mock binaries exercise the entire deployment script without contacting AWS.

GitHub Actions supplies the definitive native checks unavailable in an offline sandbox:

```text
terraform fmt -recursive
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
TFLint
Go race tests
Checkov
AWS-backed plan on same-repository pull requests
manual environment deployment through OIDC
```

See `TERRAFORM_TEST_REPORT.md` for the exact executed and deferred test matrix.


See [`TERRAFORM_MODULE_DEEP_AUDIT.md`](TERRAFORM_MODULE_DEEP_AUDIT.md) for the complete module-by-module review.
