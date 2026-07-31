# Checkov final policy remediation validation

**Date:** July 31, 2026  
**Scope:** GitHub security run #31, Terraform findings `CKV2_AWS_50` and `CKV2_AWS_3`

## Reported failures

1. `CKV2_AWS_50` — `module.redis.aws_elasticache_replication_group.this`
2. `CKV2_AWS_3` — `aws_guardduty_detector.this`

## Implemented controls

### Redis Multi-AZ automatic failover

- `automatic_failover_enabled = true`
- `multi_az_enabled = true`
- `replicas` validation requires a whole number from 1 through 5
- Development now uses one replica; production continues to use two
- Root input validation rejects zero replicas

### GuardDuty organization coverage

- Added `aws_guardduty_organization_configuration.this`
- Connected it to `aws_guardduty_detector.this.id`
- Set `auto_enable_organization_members = "ALL"`
- Added `enable_guardduty_organization_auto_enrollment`, default `false`
- The switch must be enabled only in the delegated GuardDuty administrator account

## Passed offline validation

- Security remediation validator: 156 checks
- Workflow discovery regression: 6 scenarios
- Terraform Go tests: pass
- Terraform Go race detector: pass
- Go vet: pass
- Terraform module contracts: 25 modules, 31 root instances
- GitHub workflow validation: 5 workflows
- Documentation links: 169
- Repository static checks: 69 passed, 0 failed
- Python compilation and shell syntax: pass

## Environment-limited checks

Native Checkov and Terraform provider validation could not run in this sandbox because the required binaries/packages are unavailable from its package mirror. Application and frontend test commands also require dependencies that are not installed in the extracted archive. The GitHub workflows retain those blocking checks.
