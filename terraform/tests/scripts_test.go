// Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
// Purpose: Executes bootstrap and deployment scripts in isolated fixtures to verify secure state creation, check mode, migration gating, and expected repository layout.
// Each function comment identifies the infrastructure contract being verified.

package tests

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

// Copy a repository fixture byte-for-byte into an isolated temporary test workspace.
func copyFile(t *testing.T, source, destination string, mode os.FileMode) {
	t.Helper()
	body, err := os.ReadFile(source)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Dir(destination), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(destination, body, mode); err != nil {
		t.Fatal(err)
	}
}

// Write a shell fixture and apply executable permissions so it can be invoked exactly like the real script.
func writeExecutable(t *testing.T, path, body string) {
	t.Helper()
	if err := os.WriteFile(path, []byte(body), 0o755); err != nil {
		t.Fatal(err)
	}
}

// Run a command in the supplied fixture directory and capture its combined output for assertions.
func runCommand(t *testing.T, command string, arguments []string, environment []string, directory string) (string, error) {
	t.Helper()
	cmd := exec.Command(command, arguments...)
	cmd.Dir = directory
	cmd.Env = environment
	output, err := cmd.CombinedOutput()
	return string(output), err
}

// Create the minimal repository and mocked AWS CLI layout needed to test deployment scripts without touching real cloud resources.
func prepareScriptFixture(t *testing.T) (string, string, string) {
	t.Helper()
	fixture := t.TempDir()
	fakeBin := filepath.Join(fixture, "bin")
	logFile := filepath.Join(fixture, "commands.log")
	if err := os.MkdirAll(fakeBin, 0o755); err != nil {
		t.Fatal(err)
	}

	repository := repositoryRoot(t)
	for _, relative := range []string{
		"terraform/scripts/bootstrap.sh",
		"terraform/scripts/deploy.sh",
		"terraform/global/bootstrap/main.tf",
		"terraform/global/bootstrap/variables.tf",
		"terraform/global/bootstrap/versions.tf",
		"terraform/envs/dev/terraform.tfvars",
		"Dockerfile.backend",
		"Dockerfile.frontend",
	} {
		mode := os.FileMode(0o644)
		if strings.HasSuffix(relative, ".sh") {
			mode = 0o755
		}
		copyFile(t, filepath.Join(repository, relative), filepath.Join(fixture, relative), mode)
	}
	if err := os.MkdirAll(filepath.Join(fixture, "backend"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(fixture, "frontend"), 0o755); err != nil {
		t.Fatal(err)
	}
	return fixture, fakeBin, logFile
}

// Execute backend bootstrap against mocked AWS responses and verify versioning, encryption, public-access blocking, and lockfile configuration.
func TestBootstrapScriptCreatesSecureBackend(t *testing.T) {
	fixture, fakeBin, logFile := prepareScriptFixture(t)
	writeExecutable(t, filepath.Join(fakeBin, "aws"), `#!/usr/bin/env bash
set -eu
echo "aws $*" >> "$MOCK_LOG"
if [[ "$1 $2" == "sts get-caller-identity" ]]; then echo 123456789012; exit 0; fi
if [[ "$1 $2" == "s3api head-bucket" ]]; then exit 1; fi
if [[ "$1 $2" == "s3api get-bucket-versioning" ]]; then echo Enabled; exit 0; fi
if [[ "$1 $2" == "s3api get-bucket-encryption" ]]; then echo aws:kms; exit 0; fi
exit 0
`)
	writeExecutable(t, filepath.Join(fakeBin, "terraform"), `#!/usr/bin/env bash
set -eu
echo "terraform $*" >> "$MOCK_LOG"
if [[ "$*" == *"output -raw kms_key_arn"* ]]; then
  echo arn:aws:kms:us-east-1:123456789012:key/bootstrap-key
fi
`)

	environment := append(os.Environ(),
		"PATH="+fakeBin+":"+os.Getenv("PATH"),
		"MOCK_LOG="+logFile,
		"AWS_REGION=us-east-1",
		"CREATE_BACKEND=true",
	)
	output, err := runCommand(t, "bash", []string{"terraform/scripts/bootstrap.sh", "dev"}, environment, fixture)
	if err != nil {
		t.Fatalf("bootstrap failed: %v\n%s", err, output)
	}

	backendPath := filepath.Join(fixture, "terraform", "envs", "dev", "backend.hcl")
	backend := read(t, backendPath)
	for _, expected := range []string{
		`bucket       = "demand-gig-engine-dev-123456789012-tfstate"`,
		`key          = "dev/terraform.tfstate"`,
		`kms_key_id   = "arn:aws:kms:us-east-1:123456789012:key/bootstrap-key"`,
		`use_lockfile = true`,
	} {
		if !strings.Contains(backend, expected) {
			t.Errorf("backend configuration missing %q", expected)
		}
	}
	commands := read(t, logFile)
	for _, expected := range []string{
		"terraform -chdir=",
		"init -backend=false",
		"apply -auto-approve",
		"init -force-copy -migrate-state",
		"s3api get-bucket-versioning",
		"s3api get-public-access-block",
		"s3api get-bucket-encryption",
	} {
		if !strings.Contains(commands, expected) {
			t.Errorf("Terraform-owned state bootstrap did not execute %q", expected)
		}
	}
	if strings.Contains(commands, "s3api create-bucket") {
		t.Error("bootstrap must not create state resources outside Terraform")
	}
}

// Verify that bootstrap check mode fails when the expected remote-state bucket or configuration is absent.
func TestBootstrapCheckModeRejectsMissingState(t *testing.T) {
	fixture, fakeBin, logFile := prepareScriptFixture(t)
	writeExecutable(t, filepath.Join(fakeBin, "aws"), `#!/usr/bin/env bash
set -eu
echo "aws $*" >> "$MOCK_LOG"
if [[ "$1 $2" == "sts get-caller-identity" ]]; then echo 123456789012; exit 0; fi
if [[ "$1 $2" == "s3api head-bucket" ]]; then exit 1; fi
exit 0
`)
	writeExecutable(t, filepath.Join(fakeBin, "terraform"), "#!/usr/bin/env bash\nexit 0\n")
	environment := append(os.Environ(),
		"PATH="+fakeBin+":"+os.Getenv("PATH"),
		"MOCK_LOG="+logFile,
		"CREATE_BACKEND=false",
	)
	output, err := runCommand(t, "bash", []string{"terraform/scripts/bootstrap.sh", "dev"}, environment, fixture)
	if err == nil {
		t.Fatalf("bootstrap check mode unexpectedly succeeded: %s", output)
	}
	if !strings.Contains(output, "does not exist") {
		t.Fatalf("unexpected bootstrap failure: %s", output)
	}
}

// Execute the deployment script in a fixture and verify migration success gates service scale-up and publication steps.
func TestDeployScriptOrchestratesMigrationBeforeScaleUp(t *testing.T) {
	fixture, fakeBin, logFile := prepareScriptFixture(t)

	writeExecutable(t, filepath.Join(fakeBin, "terraform"), `#!/usr/bin/env bash
set -eu
echo "terraform $*" >> "$MOCK_LOG"
case "$*" in
  *"state list"*) echo 'aws_s3_bucket.state' ;;
  *"output -raw kms_key_arn"*) echo 'arn:aws:kms:us-east-1:123456789012:key/bootstrap-key' ;;
  *"output -json ecr_repository_urls"*) echo '{"backend":"123456789012.dkr.ecr.us-east-1.amazonaws.com/backend","frontend":"123456789012.dkr.ecr.us-east-1.amazonaws.com/frontend"}' ;;
  *"output -raw ecs_cluster_arn"*) echo 'arn:aws:ecs:us-east-1:123456789012:cluster/demand-gig-engine-dev' ;;
  *"output -raw migration_task_definition_arn"*) echo 'arn:aws:ecs:us-east-1:123456789012:task-definition/migration:1' ;;
  *"output -raw migration_container_name"*) echo 'demand-gig-engine-dev-migration' ;;
  *"output -raw app_security_group_id"*) echo 'sg-1234567890' ;;
  *"output -json app_subnet_ids"*) echo '["subnet-a","subnet-b"]' ;;
  *"output -raw static_bucket_id"*) echo 'static-bucket' ;;
  *"output -raw cloudfront_distribution_id"*) echo 'E123456789' ;;
  *" output"*) echo 'deployment outputs' ;;
  *) : ;;
esac
`)
	writeExecutable(t, filepath.Join(fakeBin, "aws"), `#!/usr/bin/env bash
set -eu
echo "aws $*" >> "$MOCK_LOG"
if [[ "$1 $2" == "sts get-caller-identity" ]]; then echo 123456789012; exit 0; fi
if [[ "$1 $2" == "s3api head-bucket" ]]; then exit 0; fi
if [[ "$1 $2" == "s3api get-bucket-versioning" ]]; then echo Enabled; exit 0; fi
if [[ "$1 $2" == "s3api get-bucket-encryption" ]]; then echo aws:kms; exit 0; fi
if [[ "$1 $2" == "kms describe-key" ]]; then echo arn:aws:kms:us-east-1:123456789012:key/bootstrap-key; exit 0; fi
if [[ "$1 $2" == "ecr get-login-password" ]]; then echo password; exit 0; fi
if [[ "$1 $2" == "ecs run-task" ]]; then echo 'arn:aws:ecs:us-east-1:123456789012:task/migration-task'; exit 0; fi
if [[ "$1 $2" == "ecs describe-tasks" && "$*" == *"exitCode"* ]]; then echo 0; exit 0; fi
exit 0
`)
	writeExecutable(t, filepath.Join(fakeBin, "docker"), `#!/usr/bin/env bash
set -eu
echo "docker $*" >> "$MOCK_LOG"
case "$1" in
  login) cat >/dev/null ;;
  create) echo container-123 ;;
  cp)
    destination="${3%/.}"
    mkdir -p "$destination"
    echo '<html></html>' > "$destination/index.html"
    ;;
  *) : ;;
esac
`)
	writeExecutable(t, filepath.Join(fakeBin, "git"), `#!/usr/bin/env bash
set -eu
echo "git $*" >> "$MOCK_LOG"
echo deadbeef
`)

	environment := append(os.Environ(),
		"PATH="+fakeBin+":"+os.Getenv("PATH"),
		"MOCK_LOG="+logFile,
		"AWS_REGION=us-east-1",
		"CREATE_BACKEND=true",
	)
	output, err := runCommand(t, "bash", []string{"terraform/scripts/deploy.sh", "dev"}, environment, fixture)
	if err != nil {
		t.Fatalf("mock deployment failed: %v\n%s\ncommands:\n%s", err, output, read(t, logFile))
	}

	commands := read(t, logFile)
	migrationInfrastructure := strings.Index(commands, "-target=module.migration")
	migration := strings.Index(commands, "aws ecs run-task")
	finalApply := strings.LastIndex(commands, "terraform -chdir=")
	if migrationInfrastructure < 0 || migration < 0 || finalApply < 0 || !(migrationInfrastructure < migration && migration < finalApply) {
		t.Fatalf("deployment order is incorrect: migration-infra=%d migration=%d final=%d\n%s", migrationInfrastructure, migration, finalApply, commands)
	}
	for _, forbidden := range []string{"backend_desired_count=0", "worker_desired_count=0"} {
		if strings.Contains(commands, forbidden) {
			t.Fatalf("deployment unexpectedly scaled a live service to zero: %s\n%s", forbidden, commands)
		}
	}
	for _, expected := range []string{
		"migration_task_definition_arn",
		"docker build -f",
		"docker push",
		"aws ecs wait tasks-stopped",
		"aws s3 sync",
		"aws cloudfront create-invalidation",
	} {
		if !strings.Contains(commands, expected) {
			t.Errorf("deployment orchestration missing %q", expected)
		}
	}
}

// Verify that the isolated shell-test fixture contains every file and directory the scripts expect to reference.
func TestScriptFixtureContainsExpectedProjectLayout(t *testing.T) {
	fixture, _, _ := prepareScriptFixture(t)
	for _, relative := range []string{
		"terraform/scripts/bootstrap.sh",
		"terraform/scripts/deploy.sh",
		"terraform/global/bootstrap/main.tf",
		"terraform/global/bootstrap/variables.tf",
		"terraform/global/bootstrap/versions.tf",
		"terraform/envs/dev/terraform.tfvars",
		"Dockerfile.backend",
		"Dockerfile.frontend",
	} {
		if _, err := os.Stat(filepath.Join(fixture, relative)); err != nil {
			t.Errorf("fixture missing %s: %v", relative, err)
		}
	}
	_ = fmt.Sprintf("fixture=%s", fixture)
}
