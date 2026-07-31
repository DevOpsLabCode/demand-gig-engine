# Social Authentication and AWS Production Update

> **Author:** Stan Zvenigorodskiy  
> **Organization:** DevOps Lab Inc.  
> **Website:** [DevOpsLabInc.com](https://DevOpsLabInc.com)


## Implemented in the gig module

- Google, Facebook, Instagram, and TikTok OAuth provider configuration through `django-allauth`.
- Server-side OAuth code exchange, state validation, session authentication, and CSRF-protected login initiation.
- A React sign-in panel that detects configured providers, signs users out, updates the primary account type, and links additional social identities.
- Gig profiles for fans, bands/artists, venues, organizers/promoters, equipment-rental companies, and sponsors.
- Authenticated ownership references on campaigns, pledges, and sponsor commitments.
- Authorization rules requiring login for campaign creation and owner/staff access for campaign lifecycle and Facebook publishing actions.
- Anonymous campaign browsing, fan pledges, and sponsorship commitments remain available.
- Environment-only provider secrets; social-login access tokens are not stored by default.
- Optional Redis-backed cached database sessions for production.
- CloudFront/ALB proxy and allauth trusted-proxy settings for production deployment.

## AWS production design

The included architecture uses Route 53, CloudFront, ACM, WAF, Shield Standard, private S3, ALB, ECS Fargate, RDS PostgreSQL Multi-AZ, RDS Proxy, ElastiCache Redis, SQS/DLQs, EventBridge, Secrets Manager, KMS, SES, ECR, CloudWatch, X-Ray/OpenTelemetry, AWS Backup, Security Hub, GuardDuty, Config, CloudTrail, Control Tower, and separate Security Tooling and Log Archive accounts.

## Provider work required before production

1. Register each OAuth application and exact HTTPS callback URL.
2. Complete Google consent-screen configuration.
3. Complete Meta application review for Facebook permissions.
4. Verify the currently approved Instagram Login product and scopes before enabling Instagram.
5. Complete TikTok Login Kit review and register the fixed HTTPS redirect URI.
6. Store client secrets in AWS Secrets Manager and inject them into ECS tasks.
7. Verify the CloudFront/ALB `X-Forwarded-For` chain before setting `ALLAUTH_TRUSTED_PROXY_COUNT`.
8. Run the full GitHub Actions matrix and provider-specific staging smoke tests.

## Final testability and runtime hardening update

- Added `/api/health/` for ALB and container readiness checks.
- Switched the production backend image from Django `runserver` to Gunicorn.
- Added WhiteNoise static-file support and deterministic `collectstatic` execution.
- Passed Google, Facebook, Instagram, TikTok, CSRF, redirect, and optional Redis values through Docker Compose.
- Expanded social-auth tests to cover provider configuration, callback routes, linked-account serialization, avatar/profile synchronization, anonymous denial, owner/staff permissions, and authenticated pledge/sponsor attribution.
- Updated `scripts/run_full_tests.sh` to execute workflow validation, Django checks, migrations, blocking lint, pytest coverage, frontend build, and Compose validation.
- Added `scripts/run_all_tests.sh` to execute both application and security suites.
- Expanded dependency-free structural validation from 52 to 69 checks.
