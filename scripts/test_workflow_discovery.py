#!/usr/bin/env python3
"""Regression tests for governed GitHub Actions workflow discovery.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from __future__ import annotations

import importlib.util
import os
import tempfile
from pathlib import Path
from types import ModuleType

MODULE_PATH = Path(__file__).with_name("validate_security_remediation.py")


def load_validator() -> ModuleType:
    """Load the validator without executing its command-line entry point."""
    spec = importlib.util.spec_from_file_location("security_remediation_validator", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load validator module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def assert_path(actual: Path | None, expected: Path, scenario: str) -> None:
    if actual != expected:
        raise AssertionError(f"{scenario}: expected {expected}, got {actual}")


def main() -> int:
    validator = load_validator()
    original_root = validator.ROOT
    original_terraform_override = os.environ.get("TERRAFORM_WORKFLOW_PATH")
    original_security_override = os.environ.get("SECURITY_WORKFLOW_PATH")

    terraform_markers = "\n".join(
        (
            "terraform -chdir=terraform/global/bootstrap validate",
            "terraform -chdir=terraform/global/account validate",
            "AWS_TERRAFORM_PLAN_ROLE_ARN",
            "AWS_TERRAFORM_APPLY_ROLE_ARN",
            "terraform/scripts/bootstrap-account.sh",
            "terraform/scripts/deploy.sh",
        )
    )
    security_markers = "\n".join(
        (
            "python scripts/validate_security_remediation.py",
            "checkov --directory .",
            "Enforce complete Checkov policy gate",
            "DEPENDENCY_RESOLUTION_FAILED",
        )
    )

    try:
        with tempfile.TemporaryDirectory(prefix="workflow-discovery-") as temporary:
            root = Path(temporary)
            workflows = root / ".github" / "workflows"
            validator.ROOT = root
            os.environ.pop("TERRAFORM_WORKFLOW_PATH", None)
            os.environ.pop("SECURITY_WORKFLOW_PATH", None)

            conventional_terraform = workflows / "terraform.yml"
            conventional_security = workflows / "security.yml"
            write(conventional_terraform, terraform_markers)
            write(conventional_security, security_markers)
            assert_path(
                validator.find_terraform_workflow(),
                conventional_terraform,
                "conventional Terraform filename",
            )
            assert_path(
                validator.find_security_workflow(),
                conventional_security,
                "conventional security filename",
            )

            renamed_terraform = workflows / "infrastructure-pipeline.yaml"
            renamed_security = workflows / "policy-gates.yaml"
            conventional_terraform.rename(renamed_terraform)
            conventional_security.rename(renamed_security)
            assert_path(
                validator.find_terraform_workflow(),
                renamed_terraform,
                "marker-based Terraform discovery",
            )
            assert_path(
                validator.find_security_workflow(),
                renamed_security,
                "marker-based security discovery",
            )

            explicit_terraform = workflows / "custom-terraform.yml"
            explicit_security = workflows / "custom-security.yml"
            write(explicit_terraform, "name: explicit Terraform workflow\n")
            write(explicit_security, "name: explicit security workflow\n")
            os.environ["TERRAFORM_WORKFLOW_PATH"] = str(
                explicit_terraform.relative_to(root)
            )
            os.environ["SECURITY_WORKFLOW_PATH"] = str(
                explicit_security.relative_to(root)
            )
            assert_path(
                validator.find_terraform_workflow(),
                explicit_terraform,
                "TERRAFORM_WORKFLOW_PATH override",
            )
            assert_path(
                validator.find_security_workflow(),
                explicit_security,
                "SECURITY_WORKFLOW_PATH override",
            )
    finally:
        validator.ROOT = original_root
        if original_terraform_override is None:
            os.environ.pop("TERRAFORM_WORKFLOW_PATH", None)
        else:
            os.environ["TERRAFORM_WORKFLOW_PATH"] = original_terraform_override
        if original_security_override is None:
            os.environ.pop("SECURITY_WORKFLOW_PATH", None)
        else:
            os.environ["SECURITY_WORKFLOW_PATH"] = original_security_override

    print("Workflow discovery regression tests passed: 6 scenarios.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
