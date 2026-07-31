#!/usr/bin/env python3
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Parses GitHub Actions workflows and enforces safe, current action-reference conventions.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

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
    """
    Load a GitHub Actions workflow while preserving the YAML key named "on".
    
    Args:
        path: Relative API path appended to the configured service base URL.
    
    Returns:
        A JSON-compatible dictionary containing the normalized result.
    
    Raises:
        ValueError: When the documented validation or integration precondition fails.
    """
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.load(handle, Loader=yaml.BaseLoader)
    # Read the nested avatar URL only when the provider returned the expected object shape.
    if not isinstance(data, dict):
        raise ValueError("top-level YAML value must be a mapping")
    return data


def iter_steps(workflow: dict[str, Any]):
    """
    Yield every workflow step together with its job and step indexes for precise diagnostics.
    
    Args:
        workflow: Parsed GitHub Actions workflow mapping being inspected.
    
    Raises:
        ValueError: When the documented validation or integration precondition fails.
    """
    jobs = workflow.get("jobs")
    # Require at least one mapping-valued job in every GitHub Actions workflow.
    if not isinstance(jobs, dict) or not jobs:
        raise ValueError("workflow must define at least one job")
    # Process each `job_name, job` from `jobs.items()` in a deterministic order.
    for job_name, job in jobs.items():
        # Reject malformed jobs before inspecting required job-level controls.
        if not isinstance(job, dict):
            raise ValueError(f"job {job_name!r} must be a mapping")
        # Require each job to declare an explicit runner.
        if "runs-on" not in job:
            raise ValueError(f"job {job_name!r} is missing runs-on")
        # Require a timeout so a stalled workflow cannot consume runner capacity indefinitely.
        if "timeout-minutes" not in job:
            raise ValueError(f"job {job_name!r} is missing timeout-minutes")
        steps = job.get("steps")
        # Require every job to contain an ordered, non-empty step list.
        if not isinstance(steps, list) or not steps:
            raise ValueError(f"job {job_name!r} must define steps")
        yield from steps


def validate_action_reference(reference: str) -> str | None:
    """
    Reject unpinned, mutable, or unsupported GitHub Action references.
    
    Args:
        reference: GitHub Action reference in owner/repository@version form.
    
    Returns:
        The validated result described in the function summary and return annotation.
    """
    # Permit local actions and immutable Docker action references without applying marketplace version rules.
    if reference.startswith("docker://") or reference.startswith("./"):
        return None
    match = re.fullmatch(r"([^@]+)@(.+)", reference)
    # Reject malformed marketplace action references that do not use owner/repository@version syntax.
    if not match:
        return f"invalid action reference: {reference}"
    action, version = match.groups()
    expected = SUPPORTED_ACTIONS.get(action)
    # Reject unapproved action dependencies rather than silently trusting a new publisher or action.
    if expected is None:
        return f"unapproved action reference: {reference}"
    # Require the repository-approved major version to avoid accidental downgrades or mutable refs.
    if version != expected:
        return f"{action} must use {expected}, found {version}"
    return None


def main() -> int:
    """
    Run the module as a command-line validation entry point and return a process status.
    
    Returns:
        The typed result described in the function summary and return annotation.
    """
    errors: list[str] = []
    paths = sorted((*WORKFLOW_DIR.glob("*.yml"), *WORKFLOW_DIR.glob("*.yaml")))
    # Fail with usage guidance when no workflow path was provided to the validator.
    if not paths:
        print("No GitHub Actions workflows found.", file=sys.stderr)
        return 1

    # Process each `path` from `paths` in a deterministic order.
    for path in paths:
        # Collect a precise workflow validation error and continue checking the remaining files.
        try:
            workflow = load_workflow(path)
            # Process each `required` from `("name", "on", "permissions", "jobs")` in a
            # deterministic order.
            for required in ("name", "on", "permissions", "jobs"):
                # Require the workflow-level security and operational key currently being checked.
                if required not in workflow:
                    errors.append(f"{path}: missing top-level key {required!r}")
            # Reject blanket write permissions and require least-privilege token scopes.
            if workflow.get("permissions") == "write-all":
                errors.append(f"{path}: top-level write-all permission is forbidden")
            # Process each `step` from `iter_steps(workflow)` in a deterministic order.
            for step in iter_steps(workflow):
                # Reject malformed workflow steps before reading action references.
                if not isinstance(step, dict):
                    errors.append(f"{path}: every step must be a mapping")
                    continue
                reference = step.get("uses")
                # Validate every external action reference found in the step.
                if reference:
                    problem = validate_action_reference(reference)
                    # Attach the job/step location to each action-reference policy violation.
                    if problem:
                        errors.append(f"{path}: {problem}")
        except (OSError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"{path}: {exc}")

    # Print all workflow violations together and return a failing process status.
    if errors:
        print("Workflow validation failed:", file=sys.stderr)
        # Process each `error` from `errors` in a deterministic order.
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(paths)} GitHub Actions workflow files.")
    return 0


# Execute the command-line entry point only when this module is run directly.
if __name__ == "__main__":
    raise SystemExit(main())
