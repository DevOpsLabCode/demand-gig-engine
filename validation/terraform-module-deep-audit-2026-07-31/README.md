# Terraform module deep-audit evidence

This directory records the final offline validation of all 25 reusable Terraform modules and three independent roots.

- Module contracts: 25 modules, 31 root instances.
- Terraform files: 87.
- Security remediation checks: 116.
- Repository checks: 69.
- Documentation links: 160 across 53 Markdown files.
- Go tests: 36 with the race detector.

Native Terraform provider validation, TFLint, and Checkov remain blocking in GitHub Actions because their binaries/provider downloads were unavailable locally.

See `summary.json` for the complete machine-readable module inventory and `docs/TERRAFORM_MODULE_DEEP_AUDIT.md` for the human-readable findings.
