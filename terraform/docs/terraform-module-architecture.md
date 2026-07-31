# Terraform module architecture

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)


The implementation follows the production diagram and keeps every AWS concern in an independently testable module.

| Diagram component | Module | Key controls |
|---|---|---|
| VPC / subnets / NAT / endpoints | `networking` | 2–3 AZs, isolated DB routes, S3 endpoint |
| Least-privilege traffic | `security` | SG-to-SG ingress only |
| Route 53 / TLS | `acm` + root DNS | DNS validation, TLS 1.2/1.3 |
| WAF | `waf` | AWS managed rules and rate limiting |
| CDN / static assets | `cloudfront`, `s3_static` | OAC, private bucket, versioning, origin secret, authenticated viewer IP, no viewer-Host forwarding |
| Container registry | `ecr` | immutable tags, KMS, scan-on-push |
| Compute | `ecs_cluster`, `ecs_service` | Fargate, circuit breaker, CPU/memory autoscaling, exact workload permissions, exec auditing |
| PostgreSQL | `rds_postgres` | encryption, Multi-AZ in prod, Proxy, forced TLS, encrypted retained export logs |
| Redis | `redis` | TLS, KMS, replicas/Multi-AZ in prod, encrypted engine and slow logs |
| Async jobs | `sqs`, `eventbridge` | encrypted queue/DLQ, constrained scheduler role, retry and age controls |
| Email | `ses` | domain identity and DKIM |
| Secrets | `kms`, `secrets_manager`, service secrets | no plaintext secrets in tfvars; generated values remain protected in encrypted Terraform state |
| CI/CD identity | `github_oidc` | short-lived OIDC credentials |
| Monitoring | `cloudwatch`, `cloudtrail`, `guardduty`, `xray` | Metrics, audit, threat detection, tracing |
| Recovery | `backup` | encrypted daily AWS Backup plan |

## Environment isolation

`envs/dev` and `envs/prod` use separate remote-state keys, CIDRs, sizes, durability settings, and deletion protection. Production uses three AZs, NAT per AZ, Multi-AZ RDS, Redis replicas, longer backups, and protected data resources.

## Deployment sequence

1. Discover caller account and region.
2. Reconcile the state bucket and KMS key through `global/bootstrap`.
3. Initialize state with native S3 lockfiles.
4. Create KMS and ECR repositories.
5. Build and push backend/frontend images.
6. Provision the migration task and dependencies without changing live services.
7. Run a backward-compatible database migration.
8. Roll the API and worker only after migration success.
9. Publish static assets, invalidate CloudFront, and print outputs.
