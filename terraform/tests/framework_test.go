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

// Verify that every infrastructure module required by the documented production architecture is present.
func TestRequiredModulesExist(t *testing.T) {
	modules := []string{
		"acm", "alb", "backup", "cloudfront", "cloudtrail", "cloudwatch",
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

// Verify that backend bootstrap detects existing state resources, enables S3 protections, and avoids deprecated DynamoDB locking.
func TestRemoteStateBootstrapIsIdempotent(t *testing.T) {
	body := read(t, filepath.Join(root(t), "scripts", "bootstrap.sh"))
	for _, expected := range []string{
		"aws s3api head-bucket",
		"put-bucket-versioning",
		"put-public-access-block",
		"use_lockfile = true",
		"CREATE_BACKEND",
	} {
		if !strings.Contains(body, expected) {
			t.Errorf("bootstrap is missing %q", expected)
		}
	}
	if strings.Contains(body, "dynamodb_table") {
		t.Fatal("deprecated DynamoDB state locking found")
	}
}

// Verify that deployment holds services at zero capacity until the one-off database migration task succeeds.
func TestDeploymentRunsMigrationsBeforeScalingServices(t *testing.T) {
	body := read(t, filepath.Join(root(t), "scripts", "deploy.sh"))
	for _, expected := range []string{
		`backend_desired_count=0`,
		`worker_desired_count=0`,
		`aws ecs run-task`,
		`"migrate","--noinput"`,
		`aws ecs wait tasks-stopped`,
		`MIGRATION_EXIT_CODE`,
	} {
		if !strings.Contains(body, expected) {
			t.Errorf("deployment migration gate is missing %q", expected)
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
		regexp.MustCompile(`use_https_origin\s*=\s*var\.create_dns`),
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
	workflow := read(t, filepath.Join(repositoryRoot(t), ".github", "workflows", "terraform.yml"))
	for _, expected := range []string{
		"hashicorp/setup-terraform@v4",
		"terraform-linters/setup-tflint@v6",
		"terraform -chdir=terraform fmt -recursive",
		"terraform -chdir=terraform fmt -check -recursive",
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
