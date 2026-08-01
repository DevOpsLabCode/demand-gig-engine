func TestTerraformControlPlaneTrustAndLeastPrivilege(t *testing.T) {
	account := read(t, filepath.Join(root(t), "global", "account", "main.tf"))
	variables := read(t, filepath.Join(root(t), "global", "account", "variables.tf"))
	workflow := read(t, filepath.Join(repositoryRoot(t), ".github", "workflows", "terraform.yml"))

	for _, fragment := range []string{
		`resource "aws_iam_role" "terraform_plan"`,
		`policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/ReadOnlyAccess"`,
		`resource "aws_iam_role" "terraform_apply"`,
		`policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/PowerUserAccess"`,
		`sid       = "PassBoundedEnvironmentRolesToApprovedServices"`,
		`variable = "iam:PassedToService"`,
		`"backup.amazonaws.com"`,
		`"cloudtrail.amazonaws.com"`,
		`"ecs-tasks.amazonaws.com"`,
		`"monitoring.rds.amazonaws.com"`,
		`"scheduler.amazonaws.com"`,
		`"vpc-flow-logs.amazonaws.com"`,
	} {
		if !strings.Contains(account, fragment) {
			t.Errorf("Terraform control-plane foundation is missing %q", fragment)
		}
	}

	if strings.Contains(account, "policy/AdministratorAccess") {
		t.Error("Terraform apply role must not use AdministratorAccess")
	}

	if !strings.Contains(variables, `variable "allow_plan_pull_requests"`) ||
		!strings.Contains(variables, `default     = false`) {
		t.Error("direct pull-request OIDC trust must remain disabled by default")
	}

	if !strings.Contains(
		workflow,
		`if: github.event_name == 'push' && github.ref == 'refs/heads/main'`,
	) {
		t.Error(
			"Terraform workflow must restrict the AWS-backed " +
				"development plan to trusted pushes on main",
		)
	}

	// The workflow may use either:
	// 1. GitHub OIDC with dedicated plan/apply roles, or
	// 2. Static IAM-user credentials stored in GitHub Actions secrets.
	// Mixing both authentication models is not permitted.
	oidcRequirements := []string{
		`role-to-assume: ${{ secrets.AWS_TERRAFORM_PLAN_ROLE_ARN }}`,
		`role-to-assume: ${{ secrets.AWS_TERRAFORM_APPLY_ROLE_ARN }}`,
		`id-token: write`,
	}

	staticRequirements := []string{
		`aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}`,
		`aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}`,
		`aws-access-key-id: ${{ secrets.AWS_PROD_ACCESS_KEY_ID }}`,
		`aws-secret-access-key: ${{ secrets.AWS_PROD_SECRET_ACCESS_KEY }}`,
		`force-skip-oidc: true`,
		`unset-current-credentials: true`,
		`disable-retry: true`,
		`mask-aws-account-id: true`,
	}

	containsAll := func(required []string) bool {
		for _, fragment := range required {
			if !strings.Contains(workflow, fragment) {
				return false
			}
		}

		return true
	}

	oidcAuthentication := containsAll(oidcRequirements)
	staticAuthentication := containsAll(staticRequirements)

	if oidcAuthentication == staticAuthentication {
		if oidcAuthentication {
			t.Error(
				"Terraform workflow mixes OIDC role assumption with " +
					"static AWS access keys; configure exactly one " +
					"authentication model",
			)
		} else {
			t.Error(
				"Terraform workflow must configure either complete " +
					"OIDC plan/apply roles or complete static " +
					"development/production AWS credentials",
			)
		}
	}

	// Ignore comments when checking that static authentication does not
	// retain executable OIDC configuration.
	executableLines := make([]string, 0)

	for _, line := range strings.Split(workflow, "\n") {
		if !strings.HasPrefix(strings.TrimSpace(line), "#") {
			executableLines = append(executableLines, line)
		}
	}

	executableWorkflow := strings.Join(executableLines, "\n")

	if staticAuthentication {
		if strings.Contains(executableWorkflow, "role-to-assume:") {
			t.Error(
				"static AWS authentication must not retain role-to-assume",
			)
		}

		if strings.Contains(executableWorkflow, "id-token: write") {
			t.Error(
				"static AWS authentication must not request id-token: write",
			)
		}
	}

	if strings.Contains(workflow, `AWS_TERRAFORM_ROLE_ARN`) {
		t.Error(
			"Terraform workflow must not fall back to the legacy broad role",
		)
	}
}
