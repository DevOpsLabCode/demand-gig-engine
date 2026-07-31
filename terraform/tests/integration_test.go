//go:build integration

package tests

import (
	"os/exec"
	"testing"
)

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
