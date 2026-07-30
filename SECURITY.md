# Security Policy

## Supported code

Security fixes are applied to the `main` branch. Deployments should use a reviewed commit from `main`, not an unreviewed feature branch.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability, exposed credential, authentication bypass, payment flaw, or privacy issue.

Send a private report to `hello@devopslabinc.com` with:

- A concise description and affected component
- Reproduction steps or a proof of concept
- Expected and observed behavior
- Potential impact
- Any suggested remediation

Do not access, modify, or retain data that does not belong to you. Reports will be acknowledged and triaged as quickly as practical.

## Automated controls

The repository includes CodeQL, Checkov, Bandit, pip-audit, npm audit, dependency review, Dependabot, test coverage enforcement, and security report artifacts.
