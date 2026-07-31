# AWS Production Architecture — Demand Gig Engine

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)


## Architecture decision

The production customer-login path stays inside the Django gig service using `django-allauth`. This provides one implementation for Google, Facebook, Instagram, and TikTok. Amazon Cognito has first-class social federation for providers such as Google and Facebook, but it does not provide first-class TikTok or Instagram social providers; splitting customer identities between Cognito and a custom broker would complicate account linking and token handling. Cognito remains an option for internal operator/admin SSO.

## Production request flow

1. Route 53 resolves the application domain to CloudFront.
2. AWS WAF and Shield Standard protect the distribution.
3. CloudFront serves the React SPA from a private S3 origin through Origin Access Control.
4. `/api/*`, `/accounts/*`, `/admin/*`, and `/share/*` route to an ALB while all paths remain on one public hostname.
5. The ALB sends traffic only to non-root ECS Fargate Gunicorn/Django tasks in private application subnets and checks `/api/health/`.
6. Social OAuth callbacks return through the same CloudFront/ALB path. Provider client secrets are retrieved from Secrets Manager by the ECS task role.
7. RDS Proxy protects PostgreSQL from connection spikes; Redis provides sessions, cache, distributed rate limits, and worker coordination.
8. SQS and dead-letter queues isolate payment webhooks, partner webhooks, refunds, notifications, and retries from synchronous web traffic.

## AWS components

| Layer | Components | Purpose |
|---|---|---|
| Organization | AWS Organizations, Control Tower, IAM Identity Center | Separate production, development, QA, security tooling, and log archive accounts; reduce blast radius. |
| Edge | Route 53, CloudFront, ACM, AWS WAF, Shield Standard | DNS, TLS, CDN, DDoS baseline, bot/rate controls, managed rule groups. |
| Frontend | Private S3 bucket with CloudFront OAC | Static React application without public bucket access. |
| Compute | ECS on Fargate, ALB, ECR | Containerized Django API/social-auth broker and asynchronous workers without EC2 management. |
| Data | Aurora PostgreSQL or RDS PostgreSQL Multi-AZ, RDS Proxy, ElastiCache Redis | Durable transactional state, resilient connections, sessions/cache/rate limiting. |
| Async | SQS, DLQ, EventBridge, EventBridge Scheduler | Durable webhook handling, refunds, partner synchronization, campaign expiration, retries. |
| Storage | S3 + KMS + lifecycle/versioning | Media, exports, evidence, generated reports, architecture artifacts. |
| Secrets | Secrets Manager, KMS | Google/Facebook/Instagram/TikTok OAuth secrets, Stripe keys, DB credentials. |
| Email | SES | Login/support messages, campaign notifications, receipts. |
| Observability | CloudWatch, X-Ray or OpenTelemetry, alarms | Structured logs, traces, SLOs, queue depth, payment/webhook failures. |
| Security | Security Hub, GuardDuty, Inspector, Config, CloudTrail, Access Analyzer | Central detection, posture management, image scanning, audit evidence. |
| Delivery | GitHub Actions OIDC, ECR, ECS deployment | Keyless CI/CD; no long-lived AWS access keys in GitHub. |
| Recovery | AWS Backup, RDS PITR, S3 versioning, cross-account copies | Recovery from accidental deletion, ransomware, and account compromise. |

## Network design

Use three Availability Zones in production.

- **Public subnets:** internet-facing ALB, Internet Gateway routing, and one NAT Gateway per AZ.
- **Private application subnets:** ECS web and worker tasks. No inbound internet route.
- **Isolated data subnets:** PostgreSQL/RDS Proxy and Redis. No internet route.
- **VPC endpoints:** S3, ECR API/DKR, CloudWatch Logs, Secrets Manager, SSM and KMS where applicable.

### Security groups

- `alb-sg`: inbound 443 only from CloudFront origin-facing controls; outbound only to `app-sg`.
- `app-sg`: inbound only from `alb-sg`; outbound to RDS Proxy, Redis, VPC endpoints, and required HTTPS destinations.
- `db-proxy-sg`: inbound 5432 only from `app-sg`; outbound to `db-sg`.
- `db-sg`: inbound 5432 only from `db-proxy-sg`.
- `redis-sg`: inbound 6379/TLS only from `app-sg`.

## Social authentication path

- Users select Google, Facebook, Instagram, or TikTok in the React UI.
- The UI POSTs to `/accounts/<provider>/login/` with CSRF protection.
- `django-allauth` validates OAuth state and exchanges authorization codes server-side.
- Provider identities map to one Django user and one `GigUserProfile`.
- Profiles support fan, band, venue, organizer, equipment rental, and sponsor account types.
- Campaign ownership, pledges, and sponsor commitments link to authenticated users while anonymous support remains compatible.
- OAuth access tokens are not stored by default. Separate explicit “connect account for publishing” flows should be used when long-lived API access is required.
- Campaign creation requires authentication; campaign lifecycle and publishing actions require owner or staff authorization. Anonymous fan pledges and sponsorship interest remain supported.

## Scaling policy

- ECS web tasks: minimum 3 tasks across three AZs; target tracking on ALB request count, CPU, and latency.
- ECS workers: scale on SQS queue depth and age of oldest message.
- PostgreSQL: Multi-AZ, encrypted storage, automated backups, Performance Insights; add read replicas only when reads justify them.
- Redis: Multi-AZ replication group with automatic failover and TLS.
- CloudFront: cache immutable frontend assets aggressively; do not cache authenticated API responses.

## Deployment sequence

1. GitHub Actions runs unit tests, 90% coverage gate, Checkov, Bandit, dependency audits, CodeQL, and frontend build.
2. GitHub OIDC assumes a narrowly scoped production deployment role.
3. BuildKit produces immutable backend and frontend artifacts; backend image is pushed to ECR.
4. Database migrations run as a one-off ECS task with a dedicated task role.
5. ECS performs a rolling or blue/green deployment; ALB health checks call `/api/health/` and failed tasks are replaced automatically.
6. CloudFront invalidation is limited to changed entry-point assets.
7. Post-deployment smoke tests validate `/api/auth/config/`, campaign APIs, OAuth callback routing, and webhook endpoints.

## Recommended account layout

At minimum keep **Dev**, **QA**, and **Prod** workloads in separate accounts. A production-grade landing zone should also include dedicated **Security Tooling**, **Log Archive**, and **Shared Services** accounts. Production deployment roles must not trust developer identities directly; promotion should occur through CI/CD with approvals.

## Diagram

- SVG: [`aws-production-architecture.svg`](aws-production-architecture.svg)
- PNG: [`aws-production-architecture.png`](aws-production-architecture.png)
- Graphviz source: [`aws-production-architecture.dot`](aws-production-architecture.dot)

## Authoritative references

- AWS containerized scalable web application guidance: https://docs.aws.amazon.com/solutions/building-a-containerized-and-scalable-web-application-on-aws/
- AWS Control Tower multi-account strategy: https://docs.aws.amazon.com/controltower/latest/userguide/aws-multi-account-landing-zone.html
- AWS social identity providers in Cognito: https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-social-idp.html
- AWS React SPA with S3 and CloudFront: https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/deploy-a-react-based-single-page-application-to-amazon-s3-and-cloudfront.html
- django-allauth provider support: https://docs.allauth.org/en/latest/socialaccount/providers/index.html


## Minimum production launch profile

- 3 ECS web tasks (one per AZ), 2 worker tasks, and autoscaling policies.
- RDS PostgreSQL Multi-AZ plus RDS Proxy; Aurora is optional when scale or global recovery justifies it.
- Redis Multi-AZ for cached database sessions, cache, rate limiting, and worker coordination.
- Two CloudFront origins: private S3 for the SPA and ALB for dynamic paths.
- Separate SQS queues and DLQs for payments, OAuth/account events, partner webhooks, refunds, and notifications.
- Secrets Manager rotation and KMS customer-managed keys for high-value secrets and data stores.
- WAF managed rules, rate-based rules on `/accounts/*` and `/api/auth/*`, and stricter rules for `/admin/*`.
- CloudWatch SLO alarms for 5xx rate, ALB latency, ECS task health, RDS connections, Redis memory, queue age, failed OAuth callbacks, and webhook DLQs.
