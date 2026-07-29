# Validation artifacts

- `static_checks.log` - 32 dependency-free structural checks
- `python_compile.log` - backend syntax compilation
- `typescript_check.log` - TypeScript source check with dependency declarations
- `secret_scan.log` - credential-pattern scan
- `pdf_preflight.log` and `pdf_inspect.log` - final 26-page PDF verification
- `runtime_attempt_summary.txt` - framework tests blocked by this sandbox
- `django_runtime_attempt.log`, `npm_runtime_attempt.log`, and `docker_runtime_attempt.log` - exact environment errors

See the root `TEST_REPORT.md` for interpretation and the complete test plan.
