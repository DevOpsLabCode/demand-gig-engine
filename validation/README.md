# Validation artifacts

The `*_final.log` files correspond to the July 30, 2026 validation of the social-auth/AWS production package.

Executed successfully:

- `static_checks_final.log` — 69 dependency-free repository checks
- `github_actions_validation_final.log` — four workflow files
- `python_compile_final.log` — backend and script bytecode compilation
- `shell_syntax_final.log` — application/security test scripts
- `vibesmeet_contract_tests_final.log` — two standalone contract tests
- `typescript_syntax_final.log` — 12 TypeScript/TSX source files
- `secret_scan_final.log` — high-confidence credential-pattern scan

Attempted but blocked by this sandbox:

- `python_dependency_install_attempt_final.log`
- `npm_install_attempt_final.log`
- `run_full_tests_attempt_final.log`
- `security_scan_attempt_final.log`
- `runtime_attempt_summary_final.log`

The blocked logs show package-mirror or missing-tool failures, not application test failures. See the root [`TEST_REPORT.md`](../TEST_REPORT.md) for interpretation and the exact commands to run in GitHub Actions or an internet-connected development environment.
