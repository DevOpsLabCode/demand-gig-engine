# Terraform validation repair evidence

This repair addresses the GitHub Actions validation output that reported:

- inconsistent conditional result types in `modules/ecs_service/main.tf`;
- undefined child-module provider declarations for explicitly passed AWS provider configurations; and
- deprecated `data.aws_region.current.name` references under AWS provider 6.x.

Changes:

1. The optional X-Ray sidecar is appended through a filtered `for` expression and `concat`, avoiding conditional tuples with different lengths.
2. The ACM and WAF child modules now explicitly declare the `hashicorp/aws` provider source.
3. All regional lookups use `data.aws_region.current.region`.

Local repository validators and Go tests passed. Native Terraform CLI was unavailable in this execution environment, so `terraform fmt -check`, `terraform init`, and `terraform validate` must run in GitHub Actions as the final provider-backed verification.
