# Production environment prerequisites

`terraform.tfvars` is deliberately fail-closed. The production readiness check rejects a plan until these values are replaced with approved production facts:

- `payment_provider` must not be `fake`;
- `alarm_email` must be a monitored and confirmable endpoint;
- `domain_name` and `hosted_zone_id` must identify an owned public Route 53 zone, **or** both existing ACM certificate ARNs must be supplied;
- `terraform/global/account` must already own the GitHub OIDC provider, GuardDuty detector/features, and enhanced ECR scanning;
- Stripe/OAuth/Meta/VibesMeet credentials must be written to the generated Secrets Manager secret through the secure deployment input path.

Do not weaken `enforce_production_readiness` to make a plan pass. Supply the missing production inputs instead.
