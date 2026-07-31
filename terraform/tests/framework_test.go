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

func root(t *testing.T) string {
	t.Helper()
	path, err := filepath.Abs("..")
	if err != nil {
		t.Fatal(err)
	}
	return path
}

func repositoryRoot(t *testing.T) string {
	t.Helper()
	return filepath.Dir(root(t))
}

func read(t *testing.T, path string) string {
	t.Helper()
	body, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return string(body)
}

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
	if !regexp.MustCompile(`web_acl_id\s*=\s*var\.web_acl_arn`).MatchString(cloudfront) {
		t.Error("CloudFront distribution is not attached to WAF")
	}
	if !regexp.MustCompile(`default\s*=\s*"CLOUDFRONT"`).MatchString(waf) {
		t.Error("WAF does not default to CLOUDFRONT scope")
	}
}

func TestTerraformRuntimeFilesAreIgnored(t *testing.T) {
	body := read(t, filepath.Join(repositoryRoot(t), ".gitignore"))
	for _, expected := range []string{"**/.terraform/*", "*.tfstate", "terraform/envs/*/backend.hcl"} {
		if !strings.Contains(body, expected) {
			t.Errorf(".gitignore missing %s", expected)
		}
	}
}

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
		regexp.MustCompile(`path_pattern\s*=\s*"/static\*"`),
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

func TestTerraformWorkflowExecutesNativeValidation(t *testing.T) {
	workflow := read(t, filepath.Join(repositoryRoot(t), ".github", "workflows", "terraform.yml"))
	for _, expected := range []string{
		"hashicorp/setup-terraform@v4",
		"python3 scripts/validate_terraform_contracts.py",
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

func TestECSExecPermissionsMatchEnabledServiceFeature(t *testing.T) {
	ecs := read(t, filepath.Join(root(t), "modules", "ecs_service", "main.tf"))
	variables := read(t, filepath.Join(root(t), "modules", "ecs_service", "variables.tf"))
	if !strings.Contains(ecs, "enable_execute_command             = var.enable_execute_command") {
		t.Error("ECS service does not make Exec explicit")
	}
	if !strings.Contains(ecs, "var.enable_execute_command ? [") {
		t.Error("ECS Exec permissions are not conditional")
	}
	if !regexp.MustCompile(`variable\s+"enable_execute_command"(?s).*?default\s*=\s*false`).MatchString(variables) {
		t.Error("ECS Exec must default to false while readonlyRootFilesystem is enabled")
	}
}

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

func TestDeploySupportsNonInteractiveProviderSecretInjection(t *testing.T) {
	deploy := read(t, filepath.Join(root(t), "scripts", "deploy.sh"))
	for _, expected := range []string{
		"PROVIDER_CREDENTIALS_FILE",
		"provider_credentials_secret_arn",
		"aws secretsmanager put-secret-value",
		`keys - [`,
		`jq -s '.[0] * .[1]'`,
	} {
		if !strings.Contains(deploy, expected) {
			t.Errorf("non-interactive provider secret injection missing %q", expected)
		}
	}
}

func TestApplicationOnlineContracts(t *testing.T) {
	main := read(t, filepath.Join(root(t), "main.tf"))
	alb := read(t, filepath.Join(root(t), "modules", "alb", "main.tf"))
	cloudfront := read(t, filepath.Join(root(t), "modules", "cloudfront", "main.tf"))
	security := read(t, filepath.Join(root(t), "modules", "security", "main.tf"))
	ecs := read(t, filepath.Join(root(t), "modules", "ecs_service", "main.tf"))
	deploy := read(t, filepath.Join(root(t), "scripts", "deploy.sh"))
	settings := read(t, filepath.Join(repositoryRoot(t), "backend", "config", "settings.py"))

	for _, expected := range []string{
		`resource "random_password" "origin_verify"`,
		`origin_verify_header_name = "X-Origin-Verify"`,
		`SECURE_SSL_REDIRECT     = "true"`,
		`SECURE_PROXY_SSL_HEADER_NAME = "HTTP_X_FORWARDED_VIEWER_PROTO"`,
	} {
		if !strings.Contains(main, expected) {
			t.Errorf("root online contract missing %q", expected)
		}
	}
	for _, expected := range []string{
		`path                = "/api/health/ready/"`,
		`message_body = "Forbidden"`,
		`http_header_name = var.origin_verify_header_name`,
	} {
		if !strings.Contains(alb, expected) {
			t.Errorf("ALB online contract missing %q", expected)
		}
	}
	for _, expected := range []string{
		`name  = var.origin_verify_header_name`,
		`path_pattern               = "/static*"`,
		`Managed-CachingDisabled`,
		`Managed-AllViewerExceptHostHeader`,
	} {
		if !strings.Contains(cloudfront, expected) {
			t.Errorf("CloudFront online contract missing %q", expected)
		}
	}
	if strings.Count(security, `prefix_list_ids = [data.aws_ec2_managed_prefix_list.cloudfront.id]`) != 1 {
		t.Error("ALB security group must use one CloudFront prefix-list ingress rule to stay within default quotas")
	}
	for _, expected := range []string{
		`/api/health/live/`,
		`wait_for_steady_state`,
		`tmp_initializer`,
		`readonlyRootFilesystem = true`,
	} {
		if !strings.Contains(ecs, expected) {
			t.Errorf("ECS startup contract missing %q", expected)
		}
	}
	for _, expected := range []string{
		`describe-db-proxy-targets`,
		`/api/health/ready/`,
		`/api/auth/config/`,
		`/static/admin/css/base.css`,
	} {
		if !strings.Contains(deploy, expected) {
			t.Errorf("deployment smoke contract missing %q", expected)
		}
	}
	if !strings.Contains(settings, `"config.middleware.PublicBaseURLMiddleware"`) {
		t.Error("Django is missing canonical public URL normalization behind CloudFront")
	}
}

func TestPinnedRuntimeAndProviderVersions(t *testing.T) {
	versions := read(t, filepath.Join(root(t), "versions.tf"))
	ecsVariables := read(t, filepath.Join(root(t), "modules", "ecs_service", "variables.tf"))
	workflow := read(t, filepath.Join(repositoryRoot(t), ".github", "workflows", "terraform.yml"))
	for _, expected := range []string{`required_version = "~> 1.15.0"`, `version = "~> 6.57.1"`} {
		if !strings.Contains(versions, expected) {
			t.Errorf("provider/runtime pin missing %q", expected)
		}
	}
	if !strings.Contains(workflow, `TERRAFORM_VERSION: "1.15.8"`) {
		t.Error("GitHub Actions is not pinned to Terraform 1.15.8")
	}
	if !strings.Contains(ecsVariables, `public.ecr.aws/xray/aws-xray-daemon:3.6.6`) {
		t.Error("X-Ray daemon image is not pinned")
	}
}

func TestDatabaseStartupContracts(t *testing.T) {
	rds := read(t, filepath.Join(root(t), "modules", "rds_postgres", "main.tf"))
	settings := read(t, filepath.Join(repositoryRoot(t), "backend", "config", "settings.py"))
	dev := read(t, filepath.Join(root(t), "envs", "dev", "terraform.tfvars"))
	prod := read(t, filepath.Join(root(t), "envs", "prod", "terraform.tfvars"))
	if !strings.Contains(rds, `?sslmode=require`) {
		t.Error("RDS Proxy connection does not require TLS")
	}
	for _, expected := range []string{`parse_qs(parsed.query)`, `database_options["sslmode"]`, `"CONN_HEALTH_CHECKS": True`} {
		if !strings.Contains(settings, expected) {
			t.Errorf("Django database startup settings missing %q", expected)
		}
	}
	if !strings.Contains(rds, `performance_insights_enabled    = var.performance_insights_enabled`) {
		t.Error("RDS Performance Insights is not configurable by instance class")
	}
	if !strings.Contains(dev, `db_performance_insights_enabled = false`) {
		t.Error("development must disable unsupported/expensive Performance Insights")
	}
	if !strings.Contains(prod, `db_performance_insights_enabled = true`) {
		t.Error("production must enable Performance Insights")
	}
}

func TestGitHubOIDCUsesProtectedEnvironments(t *testing.T) {
	main := read(t, filepath.Join(root(t), "main.tf"))
	oidc := read(t, filepath.Join(root(t), "modules", "github_oidc", "main.tf"))
	for _, expected := range []string{
		`create_oidc_provider    = var.create_github_oidc_provider`,
		`allowed_environments    = [var.environment]`,
		`allowed_branches        = []`,
		`allow_pull_requests     = false`,
	} {
		if !strings.Contains(main, expected) {
			t.Errorf("root OIDC trust missing %q", expected)
		}
	}
	if !strings.Contains(oidc, `PowerUserAccess`) || !strings.Contains(oidc, `iam:PassRole`) {
		t.Error("GitHub deployment role cannot perform Terraform applies and pass project task roles")
	}
}
