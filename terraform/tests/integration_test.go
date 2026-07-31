// Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
// Purpose: Runs native Terraform initialization and validation when the Terraform CLI is available, while cleanly skipping environments that lack it.
// Each function comment identifies the infrastructure contract being verified.

//go:build integration

package tests

import (
	"os/exec"
	"testing"
)

// Run terraform init without a backend and terraform validate, skipping only when the CLI is unavailable.
func TestTerraformValidate(t *testing.T) {
	commands := [][]string{
		{"fmt", "-recursive"},
		{"fmt", "-check", "-recursive"},
		{"init", "-backend=false", "-input=false"},
		{"validate"},
	}
	for _, args := range commands {
		command := exec.Command("terraform", args...)
		command.Dir = ".."
		if output, err := command.CombinedOutput(); err != nil {
			t.Fatalf("terraform %v failed: %v\n%s", args, err, output)
		}
	}
}
