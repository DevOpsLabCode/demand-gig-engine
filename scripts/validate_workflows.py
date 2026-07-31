#!/usr/bin/env python3
"""Validate the repository's GitHub Actions files without GitHub API access."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"

SUPPORTED_ACTIONS = {
    "actions/checkout": "v7",
    "actions/setup-python": "v7",
    "actions/setup-node": "v7",
    "actions/upload-artifact": "v6",
    "actions/dependency-review-action": "v5",
    "github/codeql-action/init": "v4",
    "github/codeql-action/analyze": "v4",
    "github/codeql-action/upload-sarif": "v4",
    "actions/setup-go": "v6",
    "hashicorp/setup-terraform": "v4",
    "terraform-linters/setup-tflint": "v6",
    "aws-actions/configure-aws-credentials": "v6",
    "bridgecrewio/checkov-action": "v12",
}


def load_workflow(path: Path) -> dict[str, Any]:
    # BaseLoader keeps the key `on` as a string instead of YAML 1.1 boolean True.
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.load(handle, Loader=yaml.BaseLoader)
    if not isinstance(data, dict):
        raise ValueError("top-level YAML value must be a mapping")
    return data


def iter_steps(workflow: dict[str, Any]):
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        raise ValueError("workflow must define at least one job")
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            raise ValueError(f"job {job_name!r} must be a mapping")
        if "runs-on" not in job:
            raise ValueError(f"job {job_name!r} is missing runs-on")
        if "timeout-minutes" not in job:
            raise ValueError(f"job {job_name!r} is missing timeout-minutes")
        steps = job.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ValueError(f"job {job_name!r} must define steps")
        yield from steps


def validate_action_reference(reference: str) -> str | None:
    if reference.startswith("docker://") or reference.startswith("./"):
        return None
    match = re.fullmatch(r"([^@]+)@(.+)", reference)
    if not match:
        return f"invalid action reference: {reference}"
    action, version = match.groups()
    expected = SUPPORTED_ACTIONS.get(action)
    if expected is None:
        return f"unapproved action reference: {reference}"
    if version != expected:
        return f"{action} must use {expected}, found {version}"
    return None


def main() -> int:
    errors: list[str] = []
    paths = sorted((*WORKFLOW_DIR.glob("*.yml"), *WORKFLOW_DIR.glob("*.yaml")))
    if not paths:
        print("No GitHub Actions workflows found.", file=sys.stderr)
        return 1

    for path in paths:
        try:
            workflow = load_workflow(path)
            for required in ("name", "on", "permissions", "jobs"):
                if required not in workflow:
                    errors.append(f"{path}: missing top-level key {required!r}")
            if workflow.get("permissions") == "write-all":
                errors.append(f"{path}: top-level write-all permission is forbidden")
            for step in iter_steps(workflow):
                if not isinstance(step, dict):
                    errors.append(f"{path}: every step must be a mapping")
                    continue
                reference = step.get("uses")
                if reference:
                    problem = validate_action_reference(reference)
                    if problem:
                        errors.append(f"{path}: {problem}")
        except (OSError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"{path}: {exc}")

    if errors:
        print("Workflow validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(paths)} GitHub Actions workflow files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
