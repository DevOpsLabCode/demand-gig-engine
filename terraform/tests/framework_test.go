// Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
// Purpose: Enforces repository-wide infrastructure contracts for modules, environment defaults, IAM, networking, observability, deployment order, and production safety controls.
// Each function comment identifies the infrastructure contract being verified.

package tests

import (
	"bufio"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"testing"
)

// Return the Terraform framework directory used by infrastructure contract tests.
func root(t *testing.T) string {
	t.Helper()
	path, err := filepath.Abs("..")
	if err != nil {
		t.Fatal(err)
	}
	return path
}

// Return the repository root so tests can compare Terraform with application, container, and workflow files.
func repositoryRoot(t *testing.T) string {
	t.Helper()
	return filepath.Dir(root(t))
}

// Read a fixture file and fail the current test immediately when it cannot be loaded.
func read(t *testing.T, path string) string {
	t.Helper()
	body, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return string(body)
}

// Locate a governed workflow by security-critical content instead of a filename.
// This supports both split workflows and the consolidated python-package workflow.
func workflowWithMarkers(t *testing.T, markers ...string) string {
	t.Helper()
	directory := filepath.Join(repositoryRoot(t), ".github", "workflows")
	entries, err := os.ReadDir(directory)
	if err != nil {
		t.Fatal(err)
	}
	paths := make([]string, 0, len(entries))
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		extension := filepath.Ext(entry.Name())
		if extension == ".yml" || extension == ".yaml" {
			paths = append(paths, filepath.Join(directory, entry.Name()))
		}
	}
	sort.Strings(paths)
	for _, path := range paths {
		body := read(t, path)
		matches := true
		for _, marker := range markers {
			if !strings.Contains(body, marker) {
				matches = false
				break
			}
		}
		if matches {
			return body
		}
	}
	t.Fatalf("no workflow contains required markers: %s", strings.Join(markers, ", "))
	return ""
}

// Verify that every infrastructure module required by the documented production architecture is present.
func TestRequiredModulesExist(t *testing.T) {
	modules := []string{
		"access_logs", "acm", "alb", "backup", "cloudfront", "cloudtrail", "cloudwatch",
		"ecr", "ecs_cluster", "ecs_service", "eventbridge", "github_oidc",
		"guardduty", "kms", "networking", "rds_postgres", "redis", "route53",
		"s3_static", "secrets_manager", "security", "ses", "sqs", "waf", "xray",
	}
	for _, module := range modules {
		for _, filename := range []string{"main.tf", "variables.tf"} {
			if _, err := os.Stat(filepath.Join(root(t), "modules", module, filename)); err != nil {
				t.Errorf("missing %s/%s", module, filename)
			}
		}
	}
}

// Verify that development and production variable files declare the required environment-specific settings.
func TestEnvironmentTfvarsAreComplete(t *testing.T) {
	required := []string{
		"environment", "vpc_cidr", "backend_image", "backend_cpu",
		"backend_desired_count", "worker_desired_count", "db_instance_class",
		"deletion_protection", "schedule_enabled", "enable_guardduty",
	}
	for _, environment := range []string{"dev", "prod"} {
		body := read(t, filepath.Join(root(t), "envs", environment, "terraform.tfvars"))
		for _, key := range required {
			if !regexp.MustCompile(`(?m)^` + regexp.QuoteMeta(key) + `\s*=`).MatchString(body) {
				t.Errorf("%s missing %s", environment, key)
			}
		}
		if !regexp.MustCompile(`(?m)^environment\s*=\s*"` + regexp.QuoteMeta(environment) + `"\s*$`).MatchString(body) {
			t.Errorf("%s environment value is incorrect", environment)
		}
	}
}

// Verify that production defaults enable multi-AZ capacity, redundant workers, and deletion protection.
func TestProductionSafetyDefaults(t *testing.T) {
	body := read(t, filepath.Join(root(t), "envs", "prod", "terraform.tfvars"))
	expected := map[string]string{
		"nat_gateway_per_az":    "true",
		"backend_desired_count": "2",
		"db_multi_az":           "true",
		"redis_replicas":        "2",
		"deletion_protection":   "true",
	}
	for key, value := range expected {
		pattern := regexp.MustCompile(`(?m)^` + regexp.QuoteMeta(key) + `\s*=\s*` + regexp.QuoteMeta(value) + `\s*$`)
		if !pattern.MatchString(body) {
			t.Errorf("production safety setting missing: %s = %s", key, value)
		}
	}
}

// Scan repository files for AWS access keys, secret-key assignments, and private-key material.
func TestNoHardCodedCredentials(t *testing.T) {
	credentialPatterns := []*regexp.Regexp{
		regexp.MustCompile(`AKIA[0-9A-Z]{16}`),
		regexp.MustCompile(`(?i)aws_secret_access_key\s*=`),
		regexp.MustCompile(`-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----`),
	}
	err := filepath.Walk(repositoryRoot(t), func(path string, info os.FileInfo, walkErr error) error {
		if walkErr != nil || info.IsDir() || strings.Contains(path, string(filepath.Separator)+".terraform"+string(filepath.Separator)) {
			return walkErr
		}
		body, readErr := os.ReadFile(path)
		if readErr != nil {
			return readErr
		}
		for _, pattern := range credentialPatterns {
			if pattern.Match(body) {
				t.Errorf("credential pattern %q found in %s", pattern, path)
			}
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
}

// Verify that backend bootstrap delegates ownership to the KMS-protected Terraform
// bootstrap root, verifies existing controls, and uses native S3 lock files.
func TestRemoteStateBootstrapIsIdempotent(t *testing.T) {
	body := read(t, filepath.Join(root(t), "scripts", "bootstrap.sh"))
	for _, expected := range []string{
		"aws s3api head-bucket",
		"get-bucket-versioning",
		"get-public-access-block",
		"get-bucket-encryption",
		"global/bootstrap",
		`terraform -chdir="$BOOTSTRAP_DIR" apply`,
		"-migrate-state",
		"kms_key_id",
		"use_lockfile = true",
		"CREATE_BACKEND",
	} {
		if !strings.Contains(body, expected) {
			t.Errorf("bootstrap is missing %q", expected)
		}
	}
	for _, forbidden := range []string{"dynamodb_table", "s3api create-bucket", "put-bucket-encryption"} {
		if strings.Contains(body, forbidden) {
			t.Fatalf("bootstrap contains a competing ad-hoc state path: %s", forbidden)
		}
	}
}

// Verify that deployment runs backward-compatible migrations before updating live services.
func TestDeploymentRunsMigrationsBeforeUpdatingServices(t *testing.T) {
	body := read(t, filepath.Join(root(t), "scripts", "deploy.sh"))
	for _, expected := range []string{
		`fmt -check -recursive -diff`,
		`-target=module.migration`,
		`aws ecs run-task`,
		`"migrate","--noinput"`,
		`aws ecs wait tasks-stopped`,
		`MIGRATION_EXIT_CODE`,
	} {
		if !strings.Contains(body, expected) {
			t.Errorf("deployment migration gate is missing %q", expected)
		}
	}
	for _, forbidden := range []string{`backend_desired_count=0`, `worker_desired_count=0`} {
		if strings.Contains(body, forbidden) {
			t.Fatalf("deployment must not scale live services to zero before migration: %s", forbidden)
		}
	}
}

// Verify that the frontend image uses a build stage and serves only compiled assets from unprivileged Nginx.
func TestFrontendImageContainsProductionAssets(t *testing.T) {
	body := read(t, filepath.Join(repositoryRoot(t), "Dockerfile.frontend"))
	for _, expected := range []string{
		"AS build",
		"RUN npm run build",
		"nginxinc/nginx-unprivileged",
		"COPY --from=build /app/dist /usr/share/nginx/html",
	} {
		if !strings.Contains(body, expected) {
			t.Errorf("frontend production image is missing %q", expected)
		}
	}
}

// Verify that the ECS worker runs the SQS processor and EventBridge Scheduler emits campaign-expiry jobs.
func TestAsyncWorkerAndSchedulerAreConnected(t *testing.T) {
	main := read(t, filepath.Join(root(t), "main.tf"))
	eventbridge := read(t, filepath.Join(root(t), "modules", "eventbridge", "main.tf"))
	workerCommand := regexp.MustCompile(`command\s*=\s*\[\s*"python"\s*,\s*"manage\.py"\s*,\s*"process_tasks"\s*\]`)
	if !workerCommand.MatchString(main) {
		t.Error("worker does not run the SQS processor")
	}
	if !strings.Contains(eventbridge, "aws_scheduler_schedule") {
		t.Error("scheduler resource is missing")
	}
	schedulerInput := regexp.MustCompile(`input\s*=\s*jsonencode\(\{\s*type\s*=\s*"campaign\.expiry\.scan"\s*\}\)`)
	if !schedulerInput.MatchString(eventbridge) {
		t.Error("scheduler does not send the campaign expiry event")
	}
}

// Verify that OAuth, payment, database, and Django secrets are injected into runtime tasks rather than embedded in images.
func TestSocialAndRuntimeSecretsAreInjected(t *testing.T) {
	main := read(t, filepath.Join(root(t), "main.tf"))
	for _, expected := range []string{
		"GOOGLE_OAUTH_CLIENT_ID",
		"FACEBOOK_OAUTH_CLIENT_SECRET",
		"INSTAGRAM_OAUTH_CLIENT_ID",
		"TIKTOK_OAUTH_CLIENT_KEY",
		"STRIPE_SECRET_KEY",
		"DATABASE_URL",
		"SECRET_KEY",
	} {
		if !strings.Contains(main, expected) {
			t.Errorf("root module does not inject %s", expected)
		}
	}
}

// Reject compressed one-line Terraform blocks that are difficult to review, document, and validate safely.
func TestTerraformFilesHaveMultilineBlocks(t *testing.T) {
	var problems []string
	err := filepath.Walk(root(t), func(path string, info os.FileInfo, walkErr error) error {
		if walkErr != nil || info.IsDir() || filepath.Ext(path) != ".tf" {
			return walkErr
		}
		scanner := bufio.NewScanner(strings.NewReader(read(t, path)))
		lineNumber := 0
		for scanner.Scan() {
			lineNumber++
			line := scanner.Text()
			if strings.Contains(line, `} resource "`) || strings.Contains(line, `} module "`) || strings.Contains(line, `} variable "`) {
				problems = append(problems, path+":"+strconv.Itoa(lineNumber))
			}
		}
		return scanner.Err()
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(problems) > 0 {
		sort.Strings(problems)
		t.Fatalf("compressed adjacent HCL blocks found: %v", problems)
	}
}

// Verify that CloudFront, WAF, ALB, and security-group relationships match the documented edge-security design.
func TestEdgeProtectionMatchesArchitecture(t *testing.T) {
	main := read(t, filepath.Join(root(t), "main.tf"))
	security := read(t, filepath.Join(root(t), "modules", "security", "main.tf"))
	cloudfront := read(t, filepath.Join(root(t), "modules", "cloudfront", "main.tf"))
	waf := read(t, filepath.Join(root(t), "modules", "waf", "variables.tf"))

	for _, expected := range []string{
		`providers = {aws = aws.us_east_1}`,
		`web_acl_arn = module.waf.arn`,
	} {
		compact := regexp.MustCompile(`\s+`).ReplaceAllString(main, " ")
		if !strings.Contains(compact, expected) {
			t.Errorf("root edge configuration missing %q", expected)
		}
	}
	if !strings.Contains(security, "com.amazonaws.global.cloudfront.origin-facing") {
		t.Error("ALB security group is not restricted to the CloudFront origin-facing prefix list")
	}
	if regexp.MustCompile(`(?s)ingress\s*\{[^}]*cidr_blocks\s*=\s*\[\s*"0\.0\.0\.0/0"`).MatchString(security) {
		t.Error("public ALB ingress was found")
	}
	if !strings.Contains(cloudfront, "web_acl_id = var.web_acl_arn") {
		t.Error("CloudFront distribution is not attached to WAF")
	}
	if !regexp.MustCompile(`default\s*=\s*"CLOUDFRONT"`).MatchString(waf) {
		t.Error("WAF does not default to CLOUDFRONT scope")
	}
}

// Verify that local state, plans, lock artifacts, and generated Terraform runtime files cannot be committed accidentally.
func TestTerraformRuntimeFilesAreIgnored(t *testing.T) {
	body := read(t, filepath.Join(repositoryRoot(t), ".gitignore"))
	for _, expected := range []string{"**/.terraform/*", "*.tfstate", "terraform/envs/*/backend.hcl"} {
		if !strings.Contains(body, expected) {
			t.Errorf(".gitignore missing %s", expected)
		}
	}
}

// Verify encrypted CloudFront-to-origin traffic and SPA fallback behavior for client-side routes.
func TestCloudFrontOriginTLSAndSpaRouting(t *testing.T) {
	main := read(t, filepath.Join(root(t), "main.tf"))
	cloudfront := read(t, filepath.Join(root(t), "modules", "cloudfront", "main.tf"))

	patterns := []*regexp.Regexp{
		regexp.MustCompile(`origin_domain\s*=\s*var\.domain_name\s*==\s*""\s*\?\s*""\s*:\s*"origin\.\$\{var\.domain_name\}"`),
		regexp.MustCompile(`module\s+"acm_viewer"`),
		regexp.MustCompile(`module\s+"acm_origin"`),
		regexp.MustCompile(`providers\s*=\s*\{\s*aws\s*=\s*aws\.us_east_1\s*\}`),
		regexp.MustCompile(`certificate_arn\s*=\s*module\.acm_origin\.certificate_arn`),
		regexp.MustCompile(`certificate_arn\s*=\s*module\.acm_viewer\.certificate_arn`),
		regexp.MustCompile(`use_https_origin\s*=\s*module\.acm_origin\.certificate_arn\s*!=\s*null`),
		regexp.MustCompile(`module\s+"route53_origin"`),
	}
	for _, pattern := range patterns {
		if !pattern.MatchString(main) {
			t.Errorf("root origin TLS configuration missing pattern %s", pattern)
		}
	}
	cloudfrontPatterns := []*regexp.Regexp{
		regexp.MustCompile(`resource\s+"aws_cloudfront_function"\s+"spa_rewrite"`),
		regexp.MustCompile(`function_arn\s*=\s*aws_cloudfront_function\.spa_rewrite\.arn`),
		regexp.MustCompile(`path_pattern\s*=\s*"/share\*"`),
		regexp.MustCompile(`for_each\s*=\s*toset\(\[\s*"/api\*"\s*,\s*"/accounts\*"\s*,\s*"/admin\*"\s*\]\)`),
	}
	for _, pattern := range cloudfrontPatterns {
		if !pattern.MatchString(cloudfront) {
			t.Errorf("CloudFront routing missing pattern %s", pattern)
		}
	}
	if strings.Contains(cloudfront, "custom_error_response") {
		t.Error("distribution-wide SPA error rewriting would corrupt API error responses")
	}
}

// Verify encryption, private storage, retention, and tracing controls for runtime data and telemetry.
func TestRuntimeStorageAndTracingSecurity(t *testing.T) {
	main := read(t, filepath.Join(root(t), "main.tf"))
	s3 := read(t, filepath.Join(root(t), "modules", "s3_static", "main.tf"))
	ecs := read(t, filepath.Join(root(t), "modules", "ecs_service", "main.tf"))

	rootPatterns := []*regexp.Regexp{
		regexp.MustCompile(`kms_key_arn\s*=\s*module\.kms\.key_arn`),
		regexp.MustCompile(`create_tls_policy\s*=\s*true`),
		regexp.MustCompile(`AWS_XRAY_ENABLED\s*=\s*"true"`),
		regexp.MustCompile(`AWS_XRAY_DAEMON_ADDRESS\s*=\s*"127\.0\.0\.1:2000"`),
	}
	for _, pattern := range rootPatterns {
		if !pattern.MatchString(main) {
			t.Errorf("root runtime hardening missing pattern %s", pattern)
		}
	}
	for _, expected := range []string{
		`kms_master_key_id = var.kms_key_arn`,
		`variable = "aws:SecureTransport"`,
		`resource "aws_s3_bucket_policy" "tls"`,
	} {
		if !strings.Contains(s3, expected) {
			t.Errorf("S3 hardening missing %q", expected)
		}
	}
	for _, expected := range []string{
		`"kms:GenerateDataKey"`,
		`"xray:PutTraceSegments"`,
		`"xray-daemon"`,
		`sourceVolume`,
	} {
		if !strings.Contains(ecs, expected) {
			t.Errorf("ECS runtime hardening missing %q", expected)
		}
	}
}

// Verify that autoscaling policies and the dedicated migration task definition are both wired into the root stack.
func TestAutoscalingAndMigrationTaskDefinitions(t *testing.T) {
	ecs := read(t, filepath.Join(root(t), "modules", "ecs_service", "main.tf"))
	combined := read(t, filepath.Join(root(t), "main.tf")) + read(t, filepath.Join(root(t), "outputs.tf")) + read(t, filepath.Join(root(t), "scripts", "deploy.sh"))

	if strings.Contains(ecs, `split(" / ", var.cluster_arn)`) {
		t.Error("ECS autoscaling resource ID uses an invalid cluster ARN delimiter")
	}
	if !regexp.MustCompile(`element\(reverse\(split\("/",\s*var\.cluster_arn\)\),\s*0\)`).MatchString(ecs) {
		t.Error("ECS autoscaling resource ID does not extract the cluster name")
	}
	patterns := []*regexp.Regexp{
		regexp.MustCompile(`module\s+"migration"`),
		regexp.MustCompile(`enable_health_check\s*=\s*false`),
		regexp.MustCompile(`enable_xray\s*=\s*false`),
		regexp.MustCompile(`migration_task_definition_arn`),
		regexp.MustCompile(`migration_container_name`),
	}
	for _, pattern := range patterns {
		if !pattern.MatchString(combined) {
			t.Errorf("migration task orchestration missing pattern %s", pattern)
		}
	}
}

// Verify that CI runs native Terraform formatting, initialization, and validation rather than relying only on text checks.
func TestTerraformWorkflowExecutesNativeValidation(t *testing.T) {
	workflow := workflowWithMarkers(t, "terraform -chdir=terraform/global/bootstrap validate", "AWS_TERRAFORM_PLAN_ROLE_ARN", "AWS_TERRAFORM_APPLY_ROLE_ARN")
	for _, expected := range []string{
		"hashicorp/setup-terraform@v4",
		"terraform-linters/setup-tflint@v6",
		"terraform -chdir=terraform fmt -check -recursive -diff",
		"terraform -chdir=terraform init -backend=false -input=false",
		"terraform -chdir=terraform validate",
		"tflint --chdir=terraform --recursive",
		"go test -race -count=1 -v ./...",
		"bridgecrewio/checkov-action@v12",
	} {
		if !strings.Contains(workflow, expected) {
			t.Errorf("Terraform workflow missing %q", expected)
		}
	}
}

// Reject malformed inline Terraform objects whose missing separators can hide configuration mistakes.
func TestTerraformInlineObjectsHaveSeparators(t *testing.T) {
	patterns := []*regexp.Regexp{
		regexp.MustCompile(`Version[ \t]*=[ \t]*"[^"]+"[ \t]+Statement[ \t]*=`),
		regexp.MustCompile(`Effect[ \t]*=[ \t]*"[^"]+"[ \t]+Action[ \t]*=`),
		regexp.MustCompile(`Action[ \t]*=[ \t]*\[[^\]\n]*\][ \t]+Resource[ \t]*=`),
	}
	err := filepath.Walk(root(t), func(path string, info os.FileInfo, walkErr error) error {
		if walkErr != nil || info.IsDir() || filepath.Ext(path) != ".tf" {
			return walkErr
		}
		body := read(t, path)
		for _, pattern := range patterns {
			if pattern.MatchString(body) {
				t.Errorf("HCL object assignments without comma/newline separators found in %s: %s", path, pattern)
			}
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
}

// Verify that production browser requests default to the same-origin API path unless an explicit build-time override is supplied.
func TestFrontendDefaultsToSameOriginAPI(t *testing.T) {
	for _, relative := range []string{"frontend/src/api.ts", "frontend/src/components/AuthPanel.tsx"} {
		body := read(t, filepath.Join(repositoryRoot(t), filepath.FromSlash(relative)))
		if !strings.Contains(body, `import.meta.env.VITE_API_BASE ?? "/api"`) {
			t.Errorf("%s does not default to the same-origin /api path", relative)
		}
		if strings.Contains(body, `http://localhost:8000/api`) {
			t.Errorf("%s contains a production-breaking localhost API default", relative)
		}
	}
}

// Verify that ECS Exec permissions are present only where the service enables the feature.
func TestECSExecPermissionsMatchEnabledServiceFeature(t *testing.T) {
	ecs := read(t, filepath.Join(root(t), "modules", "ecs_service", "main.tf"))
	for _, permission := range []string{
		"ssmmessages:CreateControlChannel",
		"ssmmessages:CreateDataChannel",
		"ssmmessages:OpenControlChannel",
		"ssmmessages:OpenDataChannel",
	} {
		if !strings.Contains(ecs, permission) {
			t.Errorf("ECS Exec is enabled but task role is missing %s", permission)
		}
	}
}

// Verify that Nginx, Dockerfile, and Compose agree on the frontend container and host ports.
func TestFrontendContainerAndComposePortsAreConsistent(t *testing.T) {
	dockerfile := read(t, filepath.Join(repositoryRoot(t), "Dockerfile.frontend"))
	compose := read(t, filepath.Join(repositoryRoot(t), "docker-compose.yml"))
	for _, expected := range []string{
		"ARG VITE_API_BASE=/api",
		"ENV VITE_API_BASE=${VITE_API_BASE}",
		"EXPOSE 8080",
	} {
		if !strings.Contains(dockerfile, expected) {
			t.Errorf("frontend Dockerfile missing %q", expected)
		}
	}
	for _, expected := range []string{
		"VITE_API_BASE: http://localhost:8000/api",
		`- "5173:8080"`,
	} {
		if !strings.Contains(compose, expected) {
			t.Errorf("docker-compose frontend configuration missing %q", expected)
		}
	}
	if strings.Contains(compose, `- "5173:5173"`) {
		t.Error("docker-compose maps the frontend to a port not exposed by the production image")
	}
}

// Verify that DNS does not publish an IPv6 record for an IPv4-only load-balancer origin.
func TestIPv4OnlyAlbOriginDoesNotPublishAAAA(t *testing.T) {
	main := read(t, filepath.Join(root(t), "main.tf"))
	route53 := read(t, filepath.Join(root(t), "modules", "route53", "main.tf"))
	originBlock := regexp.MustCompile(`(?s)module\s+"route53_origin"\s*\{.*?create_ipv6\s*=\s*false.*?\}`)
	if !originBlock.MatchString(main) {
		t.Error("IPv4-only ALB origin must disable the Route 53 AAAA alias")
	}
	if !strings.Contains(route53, "var.enabled && var.create_ipv6") {
		t.Error("Route 53 module does not make IPv6 alias creation configurable")
	}
}

// Verify that hashed static assets are immutable while HTML receives revalidation-friendly cache headers.
func TestStaticAssetDeploymentUsesSafeCacheHeaders(t *testing.T) {
	deploy := read(t, filepath.Join(root(t), "scripts", "deploy.sh"))
	for _, expected := range []string{
		`--cache-control "public,max-age=31536000,immutable"`,
		`--exclude "index.html"`,
		`--cache-control "no-cache,no-store,must-revalidate"`,
		`aws cloudfront create-invalidation`,
	} {
		if !strings.Contains(deploy, expected) {
			t.Errorf("static deployment is missing %q", expected)
		}
	}
}

// Verify that deployment can supply provider secrets non-interactively without writing them into versioned files.
func TestDeploySupportsNonInteractiveProviderSecretInjection(t *testing.T) {
	deploy := read(t, filepath.Join(root(t), "scripts", "deploy.sh"))
	for _, expected := range []string{
		"PROVIDER_CREDENTIALS_FILE",
		"provider_credentials_secret_arn",
		"aws secretsmanager put-secret-value",
		`jq -e 'type == "object"'`,
	} {
		if !strings.Contains(deploy, expected) {
			t.Errorf("non-interactive provider secret injection missing %q", expected)
		}
	}
}

// Verify environment-aware cache and backup settings do not make development invalid or non-destroyable while production remains resilient.
func TestEnvironmentAwareDataProtection(t *testing.T) {
	redisMain := read(t, filepath.Join(root(t), "modules", "redis", "main.tf"))
	redisVars := read(t, filepath.Join(root(t), "modules", "redis", "variables.tf"))
	backupMain := read(t, filepath.Join(root(t), "modules", "backup", "main.tf"))
	rootMain := read(t, filepath.Join(root(t), "main.tf"))
	dev := read(t, filepath.Join(root(t), "envs", "dev", "terraform.tfvars"))
	prod := read(t, filepath.Join(root(t), "envs", "prod", "terraform.tfvars"))

	for _, fragment := range []string{
		"automatic_failover_enabled = true",
		"multi_az_enabled           = true",
	} {
		if !strings.Contains(redisMain, fragment) {
			t.Errorf("Redis mandatory availability control missing %q", fragment)
		}
	}
	if !strings.Contains(redisVars, "var.replicas >= 1") {
		t.Error("Redis module does not enforce at least one failover replica")
	}
	for _, fragment := range []string{
		"count = var.enable_vault_lock ? 1 : 0",
		"cold_storage_after = var.cold_storage_after_days",
	} {
		if !strings.Contains(backupMain, fragment) {
			t.Errorf("Backup environment-aware lifecycle missing %q", fragment)
		}
	}
	if !strings.Contains(rootMain, "enable_vault_lock           = var.enable_backup_vault_lock") {
		t.Error("Root module does not wire environment-specific Vault Lock")
	}
	if !regexp.MustCompile(`(?m)^redis_replicas\s*=\s*1\s*$`).MatchString(dev) {
		t.Error("Development must retain one Redis replica for Multi-AZ automatic failover")
	}
	if !regexp.MustCompile(`(?m)^enable_backup_vault_lock\s*=\s*false\s*$`).MatchString(dev) {
		t.Error("Development should not enable immutable Compliance Vault Lock")
	}
	if !regexp.MustCompile(`(?m)^enable_backup_vault_lock\s*=\s*true\s*$`).MatchString(prod) {
		t.Error("Production must enable Compliance Vault Lock")
	}
}

// Verify the framework fails unsafe production configurations instead of silently deploying demo integrations.
func TestProductionReadinessGate(t *testing.T) {
	main := read(t, filepath.Join(root(t), "main.tf"))
	prod := read(t, filepath.Join(root(t), "envs", "prod", "terraform.tfvars"))
	for _, fragment := range []string{
		`check "production_readiness"`,
		`var.payment_provider != "fake"`,
		`trimspace(var.alarm_email) != ""`,
		`trimspace(var.domain_name) != ""`,
	} {
		if !strings.Contains(main, fragment) {
			t.Errorf("production readiness gate missing %q", fragment)
		}
	}
	if !regexp.MustCompile(`(?m)^enforce_production_readiness\s*=\s*true\s*$`).MatchString(prod) {
		t.Error("Production must enforce readiness checks")
	}
}

// Verify final snapshots remain unique and all principal workload tiers have actionable alarms.
func TestRecoveryAndObservabilityCoverage(t *testing.T) {
	rds := read(t, filepath.Join(root(t), "modules", "rds_postgres", "main.tf"))
	cloudwatch := read(t, filepath.Join(root(t), "modules", "cloudwatch", "main.tf"))
	if !strings.Contains(rds, `resource "random_id" "final_snapshot"`) || !strings.Contains(rds, `${random_id.final_snapshot.hex}`) {
		t.Error("RDS final snapshot identifier is not collision-resistant")
	}
	for _, alarm := range []string{
		`resource "aws_cloudwatch_metric_alarm" "target_5xx"`,
		`resource "aws_cloudwatch_metric_alarm" "unhealthy_targets"`,
		`resource "aws_cloudwatch_metric_alarm" "ecs_memory"`,
		`resource "aws_cloudwatch_metric_alarm" "queue_age"`,
		`resource "aws_cloudwatch_metric_alarm" "dlq_messages"`,
		`resource "aws_cloudwatch_metric_alarm" "rds_free_storage"`,
		`resource "aws_cloudwatch_metric_alarm" "redis_memory"`,
		`resource "aws_cloudwatch_metric_alarm" "cloudfront_5xx"`,
		`resource "aws_cloudwatch_dashboard" "service"`,
	} {
		if !strings.Contains(cloudwatch, alarm) {
			t.Errorf("observability coverage missing %q", alarm)
		}
	}
}

// Verify deployment identities and container dependencies use explicit, non-wildcard trust and version choices.
func TestSupplyChainAndFederationDefaults(t *testing.T) {
	oidc := read(t, filepath.Join(root(t), "modules", "github_oidc", "variables.tf"))
	ecs := read(t, filepath.Join(root(t), "modules", "ecs_service", "variables.tf"))
	workflow := workflowWithMarkers(t, "terraform -chdir=terraform/global/bootstrap validate", "AWS_TERRAFORM_PLAN_ROLE_ARN", "AWS_TERRAFORM_APPLY_ROLE_ARN")
	versions := read(t, filepath.Join(root(t), "versions.tf"))

	if !regexp.MustCompile(`(?s)variable "allow_pull_requests".*?default\s*=\s*false`).MatchString(oidc) {
		t.Error("GitHub OIDC pull-request trust must default to false")
	}
	if !strings.Contains(ecs, "public.ecr.aws/xray/aws-xray-daemon:3.6.6") {
		t.Error("X-Ray daemon image must use the reviewed immutable version tag")
	}
	if !strings.Contains(workflow, `TERRAFORM_VERSION: "1.15.8"`) {
		t.Error("Terraform workflow is not pinned to the reviewed stable CLI release")
	}
	if !strings.Contains(versions, `version = "~> 6.57.1"`) {
		t.Error("AWS provider range can still select the withdrawn 6.57.0 release")
	}
}

// Verify that every resource-level control introduced by the Checkov remediation remains wired into the production stack.
func TestCheckovRemediationControls(t *testing.T) {
	checks := map[string][]string{
		"modules/alb/main.tf": {
			"enable_deletion_protection = var.deletion_protection",
			"access_logs {",
			`protocol          = "HTTPS"`,
		},
		"modules/cloudfront/main.tf": {
			"logging_config {",
			`viewer_protocol_policy     = "redirect-to-https"`,
			"#checkov:skip=CKV_AWS_310:",
			"#checkov:skip=CKV_AWS_374:",
		},
		"modules/cloudtrail/main.tf": {
			"abort_incomplete_multipart_upload",
			"sns_topic_name",
			"kms_key_id",
		},
		"modules/networking/main.tf": {
			"map_public_ip_on_launch = false",
		},
		"modules/rds_postgres/main.tf": {
			"multi_az                            = var.multi_az",
			"deletion_protection                 = var.deletion_protection",
			"iam_database_authentication_enabled = true",
		},
		"modules/ecs_service/main.tf": {
			`user                   = "app"`,
			`privileged             = false`,
			`drop = ["ALL"]`,
		},
		"modules/sqs/main.tf": {
			"kms_master_key_id",
			"aws_sqs_queue_redrive_allow_policy",
			"DenyInsecureTransport",
		},
		"modules/redis/main.tf": {
			"at_rest_encryption_enabled = true",
			"transit_encryption_enabled = true",
			"auth_token                 = random_password.auth.result",
		},
		"modules/backup/main.tf": {
			"aws_backup_vault_lock_configuration",
			"kms:GrantIsForAWSResource",
		},
		"modules/waf/main.tf": {
			"aws_wafv2_web_acl_logging_configuration",
			"redacted_fields",
			"kms_key_id        = aws_kms_key.logging.arn",
		},
	}

	for relative, required := range checks {
		body := read(t, filepath.Join(root(t), relative))
		for _, fragment := range required {
			if !strings.Contains(body, fragment) {
				t.Errorf("%s is missing remediation control %q", relative, fragment)
			}
		}
	}

	workflow := workflowWithMarkers(t, "validate_security_remediation.py", "Enforce complete Checkov policy gate", "DEPENDENCY_RESOLUTION_FAILED")
	for _, line := range strings.Split(workflow, "\n") {
		trimmed := strings.TrimSpace(line)
		if !strings.HasPrefix(trimmed, "#") && strings.Contains(trimmed, "--soft-fail") {
			t.Error("Checkov must remain a blocking security gate")
		}
	}
	for _, fragment := range []string{
		"validate_security_remediation.py",
		"DEPENDENCY_RESOLUTION_FAILED",
		"if-no-files-found: error",
	} {
		if !strings.Contains(workflow, fragment) {
			t.Errorf("security workflow is missing %q", fragment)
		}
	}
}

// Verify account-wide singleton services are owned once and environment modules only read them.
func TestAccountFoundationOwnsSingletonControls(t *testing.T) {
	account := read(t, filepath.Join(root(t), "global", "account", "main.tf"))
	oidc := read(t, filepath.Join(root(t), "modules", "github_oidc", "main.tf"))
	guardduty := read(t, filepath.Join(root(t), "modules", "guardduty", "main.tf"))
	workflow := workflowWithMarkers(t, "terraform -chdir=terraform/global/bootstrap validate", "AWS_TERRAFORM_PLAN_ROLE_ARN", "AWS_TERRAFORM_APPLY_ROLE_ARN")

	for _, fragment := range []string{
		`resource "aws_iam_openid_connect_provider" "github"`,
		`resource "aws_guardduty_detector" "this"`,
		`resource "aws_guardduty_organization_configuration" "this"`,
		`auto_enable_organization_members = "ALL"`,
		`resource "aws_guardduty_detector_feature" "runtime_monitoring"`,
		`ECS_FARGATE_AGENT_MANAGEMENT`,
		`resource "aws_ecr_registry_scanning_configuration" "this"`,
		`scan_frequency = "CONTINUOUS_SCAN"`,
	} {
		if !strings.Contains(account, fragment) {
			t.Errorf("account foundation is missing %q", fragment)
		}
	}
	if strings.Contains(oidc, `resource "aws_iam_openid_connect_provider"`) {
		t.Error("environment GitHub OIDC module must not own the account-wide provider")
	}
	if !strings.Contains(oidc, `data "aws_iam_openid_connect_provider" "github"`) {
		t.Error("environment GitHub OIDC module must read the shared provider")
	}
	if strings.Contains(guardduty, `resource "aws_guardduty_detector"`) {
		t.Error("environment GuardDuty module must not create a duplicate detector")
	}
	if !strings.Contains(guardduty, `data "aws_guardduty_detector" "this"`) {
		t.Error("environment GuardDuty module must verify the shared detector")
	}
	for _, stack := range []string{"terraform/global/bootstrap", "terraform/global/account"} {
		if !strings.Contains(workflow, `terraform -chdir=`+stack+` validate`) {
			t.Errorf("Terraform workflow does not validate independent root %s", stack)
		}
	}
}

// Verify the Terraform control plane cannot expose remote state to pull requests and cannot pass arbitrary roles.
func TestTerraformControlPlaneTrustAndLeastPrivilege(t *testing.T) {
	account := read(t, filepath.Join(root(t), "global", "account", "main.tf"))
	variables := read(t, filepath.Join(root(t), "global", "account", "variables.tf"))
	workflow := workflowWithMarkers(t, "terraform -chdir=terraform/global/bootstrap validate", "AWS_TERRAFORM_PLAN_ROLE_ARN", "AWS_TERRAFORM_APPLY_ROLE_ARN")

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
	for _, fragment := range []string{
		`if: github.event_name == 'push' && github.ref == 'refs/heads/main'`,
		`role-to-assume: ${{ secrets.AWS_TERRAFORM_PLAN_ROLE_ARN }}`,
		`role-to-assume: ${{ secrets.AWS_TERRAFORM_APPLY_ROLE_ARN }}`,
		`id-token: write`,
	} {
		if !strings.Contains(workflow, fragment) {
			t.Errorf("Terraform workflow is missing trust control %q", fragment)
		}
	}
	if strings.Contains(workflow, `AWS_TERRAFORM_ROLE_ARN`) {
		t.Error("Terraform workflow must not fall back to the legacy broad role")
	}
}

// Verify every workload IAM role is capped by the approved permissions boundary and
// the Terraform apply role cannot rewrite its own control-plane roles.
func TestWorkloadRolePermissionsBoundaries(t *testing.T) {
	rootMain := read(t, filepath.Join(root(t), "main.tf"))
	account := read(t, filepath.Join(root(t), "global", "account", "main.tf"))
	roleModules := []string{"backup", "cloudtrail", "ecs_service", "eventbridge", "github_oidc", "networking", "rds_postgres"}

	if !strings.Contains(rootMain, `permissions_boundary_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/PowerUserAccess"`) {
		t.Error("root stack must derive the partition-correct PowerUserAccess permissions boundary")
	}
	for _, module := range roleModules {
		variables := read(t, filepath.Join(root(t), "modules", module, "variables.tf"))
		main := read(t, filepath.Join(root(t), "modules", module, "main.tf"))
		if !strings.Contains(variables, `variable "permissions_boundary_arn"`) {
			t.Errorf("module %s is missing its permissions_boundary_arn contract", module)
		}
		if !strings.Contains(main, `permissions_boundary = var.permissions_boundary_arn`) {
			t.Errorf("module %s creates IAM roles without the required permissions boundary", module)
		}
	}
	for _, fragment := range []string{
		`role/${var.project_name}-dev-*`,
		`role/${var.project_name}-prod-*`,
		`sid       = "CreateBoundedEnvironmentRoles"`,
		`variable = "iam:PermissionsBoundary"`,
		`sid       = "AttachApprovedManagedPolicies"`,
		`variable = "iam:PolicyARN"`,
	} {
		if !strings.Contains(account, fragment) {
			t.Errorf("account apply policy is missing boundary control %q", fragment)
		}
	}
	for _, forbidden := range []string{
		`project_role_arn =`,
		`role/${var.project_name}-*"`,
		`iam:DeleteRolePermissionsBoundary`,
		`ManageGitHubOIDCProvider`,
	} {
		if strings.Contains(account, forbidden) {
			t.Errorf("account apply policy contains forbidden broad control %q", forbidden)
		}
	}
}

// Verify outbound email authentication and CloudTrail investigation controls are complete but cost-aware.
func TestIdentityAndAuditBoundaryControls(t *testing.T) {
	ses := read(t, filepath.Join(root(t), "modules", "ses", "main.tf"))
	cloudtrail := read(t, filepath.Join(root(t), "modules", "cloudtrail", "main.tf"))
	rootMain := read(t, filepath.Join(root(t), "main.tf"))

	for _, fragment := range []string{
		`resource "aws_ses_domain_mail_from" "this"`,
		`resource "aws_route53_record" "mail_from_mx"`,
		`resource "aws_route53_record" "mail_from_spf"`,
		`resource "aws_route53_record" "dmarc"`,
		`behavior_on_mx_failure = "RejectMessage"`,
	} {
		if !strings.Contains(ses, fragment) {
			t.Errorf("SES deliverability control missing %q", fragment)
		}
	}
	for _, fragment := range []string{
		`event_selector {`,
		`type   = "AWS::S3::Object"`,
		`dynamic "insight_selector"`,
		`ApiCallRateInsight`,
		`ApiErrorRateInsight`,
	} {
		if !strings.Contains(cloudtrail, fragment) {
			t.Errorf("CloudTrail investigation control missing %q", fragment)
		}
	}
	if !strings.Contains(rootMain, `s3_data_event_bucket_arns = var.environment == "prod"`) ||
		!strings.Contains(rootMain, `enable_insights          = var.environment == "prod"`) {
		t.Error("production-only CloudTrail data events and Insights are not wired at the root")
	}
}

// Verify destructive recovery windows are longer in production while development remains disposable.
func TestEnvironmentAwareSecretRecovery(t *testing.T) {
	main := read(t, filepath.Join(root(t), "main.tf"))
	for _, fragment := range []string{
		`secret_recovery_window_days  = var.environment == "prod" ? 30 : 7`,
		`recovery_window_in_days = var.environment == "prod" ? 30 : 7`,
	} {
		if !strings.Contains(main, fragment) {
			t.Errorf("environment-aware secret recovery missing %q", fragment)
		}
	}
}

// Verify that only this CloudFront distribution can reach the ALB target group,
// even though AWS's managed CloudFront prefix list is shared by all distributions.
func TestCloudFrontOriginBypassProtection(t *testing.T) {
	rootMain := read(t, filepath.Join(root(t), "main.tf"))
	albMain := read(t, filepath.Join(root(t), "modules", "alb", "main.tf"))
	albVariables := read(t, filepath.Join(root(t), "modules", "alb", "variables.tf"))
	cloudfrontMain := read(t, filepath.Join(root(t), "modules", "cloudfront", "main.tf"))
	cloudfrontVariables := read(t, filepath.Join(root(t), "modules", "cloudfront", "variables.tf"))
	wafMain := read(t, filepath.Join(root(t), "modules", "waf", "main.tf"))

	for label, body := range map[string]string{
		"ALB":        albVariables,
		"CloudFront": cloudfrontVariables,
	} {
		if !strings.Contains(body, `variable "origin_verify_header_value"`) ||
			!strings.Contains(body, "sensitive   = true") ||
			!strings.Contains(body, "length(var.origin_verify_header_value) >= 32") {
			t.Errorf("%s module does not enforce a sensitive high-entropy origin verification value", label)
		}
	}

	rootPatterns := []*regexp.Regexp{
		regexp.MustCompile(`resource\s+"random_password"\s+"origin_verify"`),
		regexp.MustCompile(`length\s*=\s*64`),
		regexp.MustCompile(`origin_verify_header_value\s*=\s*random_password\.origin_verify\.result`),
	}
	for _, pattern := range rootPatterns {
		if !pattern.MatchString(rootMain) {
			t.Errorf("root origin-verification wiring missing pattern %s", pattern)
		}
	}

	if !strings.Contains(cloudfrontMain, `name  = "X-Origin-Verify"`) ||
		!strings.Contains(cloudfrontMain, "value = var.origin_verify_header_value") {
		t.Error("CloudFront does not inject the protected origin-verification header")
	}
	if !strings.Contains(albMain, `http_header_name = "X-Origin-Verify"`) ||
		!strings.Contains(albMain, "values           = [var.origin_verify_header_value]") {
		t.Error("ALB forwarding rules do not require the origin-verification header")
	}
	if strings.Count(albMain, `status_code  = "403"`) < 2 {
		t.Error("ALB listeners must default-deny both HTTP-only and HTTPS origin modes")
	}
	if !strings.Contains(wafMain, `name = "x-origin-verify"`) {
		t.Error("WAF request logging does not redact the origin-verification header")
	}
}

// Verify that the edge and origin Web ACLs include reputation and SQL injection
// protections and that the regional ACL rate-limits the real forwarded viewer IP.
func TestWAFManagedRuleCoverageAndViewerRateLimit(t *testing.T) {
	wafMain := read(t, filepath.Join(root(t), "modules", "waf", "main.tf"))
	for _, expected := range []string{
		"AWSManagedRulesCommonRuleSet",
		"AWSManagedRulesAmazonIpReputationList",
		"AWSManagedRulesKnownBadInputsRuleSet",
		"AWSManagedRulesSQLiRuleSet",
		`aggregate_key_type = var.scope == "REGIONAL" ? "FORWARDED_IP" : "IP"`,
		`header_name       = "X-Origin-Viewer-IP"`,
	} {
		if !strings.Contains(wafMain, expected) {
			t.Errorf("WAF coverage missing %s", expected)
		}
	}
}

// Verify that the plan role can decrypt CMK-encrypted state and encrypt native
// S3 lock files without receiving cryptographic access to unrelated account keys.
func TestTerraformPlanRoleCanUseOnlyStateKMSKeys(t *testing.T) {
	account := read(t, filepath.Join(root(t), "global", "account", "main.tf"))
	for _, expected := range []string{
		"state_kms_aliases = [",
		`"alias/${var.project_name}-account-tfstate"`,
		`"alias/${var.project_name}-dev-tfstate"`,
		`"alias/${var.project_name}-prod-tfstate"`,
		`sid = "UseTerraformStateKeys"`,
		`"kms:Decrypt"`,
		`"kms:Encrypt"`,
		`"kms:GenerateDataKey"`,
		`variable = "kms:ResourceAliases"`,
		"values   = local.state_kms_aliases",
	} {
		if !strings.Contains(account, expected) {
			t.Errorf("Terraform plan state-key policy missing %s", expected)
		}
	}
}

// Verify that task execution no longer relies on the broad AWS-managed policy
// and is scoped to declared ECR repositories, the service log group, secrets, and key.
func TestECSExecutionRoleIsRepositoryAndLogScoped(t *testing.T) {
	ecsMain := read(t, filepath.Join(root(t), "modules", "ecs_service", "main.tf"))
	ecsVariables := read(t, filepath.Join(root(t), "modules", "ecs_service", "variables.tf"))
	rootMain := read(t, filepath.Join(root(t), "main.tf"))
	accountMain := read(t, filepath.Join(root(t), "global", "account", "main.tf"))

	if strings.Contains(ecsMain, "AmazonECSTaskExecutionRolePolicy") {
		t.Error("ECS service still attaches the broad AWS-managed execution policy")
	}
	for _, expected := range []string{
		`variable "ecr_repository_arns"`,
		"length(var.ecr_repository_arns) > 0",
	} {
		if !strings.Contains(ecsVariables, expected) {
			t.Errorf("ECS execution contract missing %s", expected)
		}
	}
	for _, expected := range []string{
		`resource "aws_iam_role_policy" "execution"`,
		`"ecr:GetAuthorizationToken"`,
		"Resource = var.ecr_repository_arns",
		`"logs:CreateLogStream"`,
		`"logs:PutLogEvents"`,
		"log-group:${aws_cloudwatch_log_group.this.name}:log-stream:*",
		"Resource = local.secret_arns",
		"Resource = var.kms_key_arn",
	} {
		if !strings.Contains(ecsMain, expected) {
			t.Errorf("ECS execution policy missing %s", expected)
		}
	}
	if strings.Count(rootMain, "ecr_repository_arns = module.ecr.repository_arns") != 3 {
		t.Error("API, worker, and migration task roles must receive project ECR repository ARNs")
	}
	if strings.Contains(accountMain, "AmazonECSTaskExecutionRolePolicy") {
		t.Error("Terraform apply role may still attach the removed broad ECS execution managed policy")
	}
}

// Verify that externally managed DNS deployments can supply an existing SES
// identity and that production cannot silently launch without outbound email.
func TestSESExistingIdentityAndProductionReadiness(t *testing.T) {
	rootMain := read(t, filepath.Join(root(t), "main.tf"))
	rootVariables := read(t, filepath.Join(root(t), "variables.tf"))
	sesVariables := read(t, filepath.Join(root(t), "modules", "ses", "variables.tf"))
	sesOutputs := read(t, filepath.Join(root(t), "modules", "ses", "outputs.tf"))

	for _, expected := range []string{
		`variable "ses_identity_arn"`,
		`^arn:[^:]+:ses:[^:]+:[0-9]{12}:identity/`,
	} {
		if !strings.Contains(rootVariables, expected) {
			t.Errorf("root SES contract missing %s", expected)
		}
	}
	for _, expected := range []string{
		"var.create_dns || var.ses_identity_arn != null",
		"existing_identity_arn = var.ses_identity_arn",
		"dmarc_rua             = var.alarm_email",
	} {
		if !strings.Contains(rootMain, expected) {
			t.Errorf("root SES readiness/wiring missing %s", expected)
		}
	}
	if !strings.Contains(sesVariables, `variable "existing_identity_arn"`) ||
		!strings.Contains(sesVariables, `check "identity_source"`) {
		t.Error("SES module does not support a mutually exclusive external identity")
	}
	if !strings.Contains(sesOutputs, "var.create_dns ? aws_ses_domain_identity.this[0].arn : var.existing_identity_arn") {
		t.Error("SES identity output does not return the configured identity source")
	}
}

// Verify that CloudFront overwrites the private viewer-IP header from the
// authenticated event context before regional WAF uses it for rate aggregation.
func TestCloudFrontAuthenticatedViewerIPHeader(t *testing.T) {
	cloudfrontMain := read(t, filepath.Join(root(t), "modules", "cloudfront", "main.tf"))
	functionCode := read(t, filepath.Join(root(t), "modules", "cloudfront", "true-client-ip.js"))
	wafMain := read(t, filepath.Join(root(t), "modules", "waf", "main.tf"))

	for _, expected := range []string{
		`resource "aws_cloudfront_function" "true_client_ip"`,
		`code    = file("${path.module}/true-client-ip.js")`,
		"function_arn = aws_cloudfront_function.true_client_ip.arn",
		`resource "aws_cloudfront_cache_policy" "api_disabled"`,
		`resource "aws_cloudfront_origin_request_policy" "api"`,
		`resource "aws_cloudfront_cache_policy" "share"`,
		`resource "aws_cloudfront_origin_request_policy" "share"`,
		"cache_policy_id          = aws_cloudfront_cache_policy.api_disabled.id",
		"origin_request_policy_id = aws_cloudfront_origin_request_policy.api.id",
		"cache_policy_id          = aws_cloudfront_cache_policy.share.id",
		"origin_request_policy_id = aws_cloudfront_origin_request_policy.share.id",
		`"X-Origin-Viewer-IP"`,
		`"Authorization"`,
		`"X-CSRFToken"`,
	} {
		if !strings.Contains(cloudfrontMain, expected) {
			t.Errorf("CloudFront true-client-IP propagation missing %s", expected)
		}
	}
	if strings.Count(cloudfrontMain, "function_arn = aws_cloudfront_function.true_client_ip.arn") != 2 {
		t.Error("true-client-IP function must be attached to API and share origin behaviors")
	}
	for _, forbidden := range []string{
		`headers      = ["Host", "X-Origin-Viewer-IP"]`,
		`headers      = ["*"]`,
		`items = ["Host"`,
	} {
		if strings.Contains(cloudfrontMain, forbidden) {
			t.Errorf("CloudFront must not forward viewer Host or wildcard headers to the TLS origin: %s", forbidden)
		}
	}
	if strings.Contains(cloudfrontMain, `headers      = ["Accept-Language", "X-Origin-Viewer-IP"]`) {
		t.Error("share viewer IP must be forwarded only by the origin request policy, not included in the cache key")
	}
	if !strings.Contains(functionCode, `event.viewer.ip`) ||
		!strings.Contains(functionCode, `request.headers["x-origin-viewer-ip"]`) {
		t.Error("CloudFront Function does not overwrite the private origin viewer-IP header")
	}
	if !strings.Contains(wafMain, `header_name       = "X-Origin-Viewer-IP"`) {
		t.Error("regional WAF is not using the authenticated CloudFront viewer-IP header")
	}
}

// Verify that stateful services publish encrypted, retained engine logs and that
// each ECS workload receives only its required queue operations.
func TestStatefulLogsAndWorkloadSpecificPermissions(t *testing.T) {
	rootDir := root(t)
	rdsMain := read(t, filepath.Join(rootDir, "modules", "rds_postgres", "main.tf"))
	redisMain := read(t, filepath.Join(rootDir, "modules", "redis", "main.tf"))
	ecsMain := read(t, filepath.Join(rootDir, "modules", "ecs_service", "main.tf"))
	rootMain := read(t, filepath.Join(rootDir, "main.tf"))

	for _, expected := range []string{
		`resource "aws_cloudwatch_log_group" "postgresql"`,
		`resource "aws_cloudwatch_log_group" "upgrade"`,
		`retention_in_days = var.log_retention_days`,
		`kms_key_id        = var.kms_key_arn`,
	} {
		if !strings.Contains(rdsMain, expected) {
			t.Errorf("RDS exported-log control missing %s", expected)
		}
	}
	for _, expected := range []string{
		`resource "aws_cloudwatch_log_group" "engine"`,
		`resource "aws_cloudwatch_log_group" "slow"`,
		`log_type         = "engine-log"`,
		`log_type         = "slow-log"`,
	} {
		if !strings.Contains(redisMain, expected) {
			t.Errorf("Redis log-delivery control missing %s", expected)
		}
	}
	for _, expected := range []string{
		`queue_statements = length(var.queue_actions) == 0 ? []`,
		`enable_ecs_managed_tags             = true`,
		`propagate_tags                      = "SERVICE"`,
		`resource "aws_appautoscaling_policy" "memory"`,
	} {
		if !strings.Contains(ecsMain, expected) {
			t.Errorf("ECS control missing %s", expected)
		}
	}
	for _, expected := range []string{
		`queue_actions = ["sqs:GetQueueAttributes", "sqs:SendMessage"]`,
		`queue_actions = ["sqs:DeleteMessage", "sqs:GetQueueAttributes", "sqs:ReceiveMessage"]`,
		`queue_actions             = []`,
	} {
		if !strings.Contains(rootMain, expected) {
			t.Errorf("root workload permission wiring missing %s", expected)
		}
	}
}
