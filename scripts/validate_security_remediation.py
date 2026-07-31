#!/usr/bin/env python3
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Guards the Terraform security controls added for the Checkov remediation.

"""Dependency-free validation of security-critical Terraform invariants.

This validator is intentionally independent of Terraform providers and cloud
credentials. It catches accidental removal of the controls that remediate the
repository's Checkov findings before the full scanner runs.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TERRAFORM = ROOT / "terraform"
ERRORS: list[str] = []
PASSES: list[str] = []


def require(path: str, *needles: str) -> None:
    """Require every security-critical text fragment in one repository file."""
    target = ROOT / path
    if not target.is_file():
        ERRORS.append(f"Missing required file: {path}")
        return
    text = target.read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        for needle in missing:
            ERRORS.append(f"{path}: missing security invariant {needle!r}")
    else:
        PASSES.append(f"{path}: {len(needles)} security invariants present")



def find_security_workflow() -> Path | None:
    """Locate the workflow even when the repository uses a custom filename.

    Resolution order: SECURITY_WORKFLOW_PATH environment override, conventional
    security.yml/security.yaml names, then the workflow containing this validator
    and the blocking Checkov command. This keeps renamed or consolidated workflows
    valid while rejecting repositories where the security gate is actually absent.
    """
    workflows = ROOT / ".github" / "workflows"
    override = os.environ.get("SECURITY_WORKFLOW_PATH", "").strip()
    if override:
        candidate = Path(override)
        if not candidate.is_absolute():
            candidate = ROOT / candidate
        return candidate if candidate.is_file() else None

    for name in ("security.yml", "security.yaml"):
        candidate = workflows / name
        if candidate.is_file():
            return candidate

    candidates: list[tuple[int, Path]] = []
    for pattern in ("*.yml", "*.yaml"):
        for candidate in workflows.glob(pattern):
            text = candidate.read_text(encoding="utf-8")
            score = sum(
                marker in text
                for marker in (
                    "python scripts/validate_security_remediation.py",
                    "checkov --directory .",
                    "Enforce complete Checkov policy gate",
                    "DEPENDENCY_RESOLUTION_FAILED",
                )
            )
            if score >= 2:
                candidates.append((score, candidate))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], str(item[1])))
    return candidates[0][1]


def require_text(path: Path, text: str, *needles: str) -> None:
    """Require security-critical fragments in a previously discovered file."""
    relative = path.relative_to(ROOT)
    missing = [needle for needle in needles if needle not in text]
    if missing:
        for needle in missing:
            ERRORS.append(f"{relative}: missing security invariant {needle!r}")
    else:
        PASSES.append(f"{relative}: {len(needles)} security invariants present")

def remove_comments_and_strings(text: str) -> str:
    """Replace HCL comments and quoted-string contents while retaining delimiters."""
    output: list[str] = []
    index = 0
    state = "code"
    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""
        if state == "code":
            if char == '"':
                state = "string"
                output.append('"')
            elif char == "#":
                state = "line_comment"
                output.append(" ")
            elif char == "/" and nxt == "/":
                state = "line_comment"
                output.extend("  ")
                index += 1
            elif char == "/" and nxt == "*":
                state = "block_comment"
                output.extend("  ")
                index += 1
            else:
                output.append(char)
        elif state == "string":
            if char == "\\":
                output.extend("  ")
                index += 1
            elif char == '"':
                state = "code"
                output.append('"')
            elif char == "\n":
                output.append("\n")
            else:
                output.append(" ")
        elif state == "line_comment":
            if char == "\n":
                state = "code"
                output.append("\n")
            else:
                output.append(" ")
        elif state == "block_comment":
            if char == "*" and nxt == "/":
                state = "code"
                output.extend("  ")
                index += 1
            else:
                output.append("\n" if char == "\n" else " ")
        index += 1
    if state in {"string", "block_comment"}:
        ERRORS.append(f"Unterminated {state.replace('_', ' ')} in Terraform source")
    return "".join(output)


def validate_delimiters(path: Path) -> None:
    """Check balanced HCL block, collection, and expression delimiters."""
    cleaned = remove_comments_and_strings(path.read_text(encoding="utf-8"))
    opening = {"{": "}", "[": "]", "(": ")"}
    closing = {value: key for key, value in opening.items()}
    stack: list[tuple[str, int]] = []
    for offset, char in enumerate(cleaned):
        if char in opening:
            stack.append((char, offset))
        elif char in closing:
            if not stack or stack[-1][0] != closing[char]:
                line = cleaned.count("\n", 0, offset) + 1
                ERRORS.append(f"{path.relative_to(ROOT)}:{line}: unexpected {char}")
                return
            stack.pop()
    if stack:
        char, offset = stack[-1]
        line = cleaned.count("\n", 0, offset) + 1
        ERRORS.append(f"{path.relative_to(ROOT)}:{line}: unclosed {char}")
    else:
        PASSES.append(f"{path.relative_to(ROOT)}: balanced HCL delimiters")


def validate_suppressions() -> None:
    """Require substantive Checkov exceptions located inside Terraform scopes."""
    pattern = re.compile(r"#checkov:skip=([A-Z0-9_]+):(.+)$")
    count = 0
    for path in sorted(TERRAFORM.rglob("*.tf")):
        depth = 0
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "#checkov:skip=" in line:
                count += 1
                match = pattern.search(line.strip())
                if not match or len(match.group(2).strip()) < 35:
                    ERRORS.append(
                        f"{path.relative_to(ROOT)}:{number}: Checkov suppression needs a specific risk justification"
                    )
                if depth <= 0 or line == line.lstrip():
                    ERRORS.append(
                        f"{path.relative_to(ROOT)}:{number}: Checkov suppression must be indented inside the resource or data block it governs"
                    )

            # Count HCL braces after removing strings and comments from this line.
            cleaned = remove_comments_and_strings(line + "\n")
            depth += cleaned.count("{") - cleaned.count("}")
            if depth < 0:
                ERRORS.append(f"{path.relative_to(ROOT)}:{number}: invalid HCL scope depth")
                depth = 0

    if count:
        PASSES.append(f"Validated {count} in-scope documented Checkov exceptions")
    else:
        ERRORS.append("No documented Checkov exceptions found")


def validate_security_group_egress() -> None:
    """Reject the dangerous all-protocol, all-destination egress combination."""
    for path in sorted(TERRAFORM.rglob("*.tf")):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\begress\s*\{(?P<body>.*?)\n\s*\}", text, re.DOTALL):
            body = match.group("body")
            unrestricted_destination = '"0.0.0.0/0"' in body or '"::/0"' in body
            all_protocols = re.search(r"protocol\s*=\s*\"-1\"", body) is not None
            if unrestricted_destination and all_protocols:
                line = text.count("\n", 0, match.start()) + 1
                ERRORS.append(
                    f"{path.relative_to(ROOT)}:{line}: unrestricted all-protocol security-group egress"
                )
    if not any("security-group egress" in item for item in ERRORS):
        PASSES.append("No unrestricted all-protocol security-group egress")


def main() -> int:
    """Validate syntax shape and the complete Checkov remediation control set."""
    tf_files = sorted(TERRAFORM.rglob("*.tf"))
    if not tf_files:
        print("No Terraform files found.", file=sys.stderr)
        return 1
    for path in tf_files:
        validate_delimiters(path)

    require(
        "terraform/modules/access_logs/main.tf",
        'data "aws_canonical_user_id" "current" {}',
        'cloudfront_log_delivery_canonical_user_id = "c4c1ede66af53448b93c283ce9448c4ba468c9432aa01d700d3878632f77d2d0"',
        "access_control_policy {",
        'permission = "FULL_CONTROL"',
    )
    require(
        "terraform/modules/alb/main.tf",
        "enable_deletion_protection = var.deletion_protection",
        "access_logs {",
        'protocol          = "HTTPS"',
        'ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"',
    )
    require(
        "terraform/modules/cloudfront/main.tf",
        "logging_config {",
        'viewer_protocol_policy     = "redirect-to-https"',
        "#checkov:skip=CKV_AWS_310:",
        "#checkov:skip=CKV_AWS_374:",
    )
    require(
        "terraform/modules/cloudtrail/main.tf",
        "abort_incomplete_multipart_upload",
        "sns_topic_name",
        "kms_master_key_id",
        "cloud_watch_logs_group_arn",
        "cloud_watch_logs_role_arn",
    )
    require(
        "terraform/modules/cloudwatch/main.tf",
        'kms_master_key_id = var.kms_key_arn',
        "AllowCloudWatchAlarmPublish",
        "DenyInsecureTransport",
    )
    require(
        "terraform/modules/ecs_cluster/main.tf",
        "retention_in_days = var.log_retention_days",
        "kms_key_id        = var.kms_key_arn",
    )
    require(
        "terraform/modules/ecs_service/main.tf",
        "retention_in_days = var.log_retention_days",
        "kms_key_id        = var.kms_key_arn",
        'user                   = "app"',
        'drop = ["ALL"]',
    )
    require(
        "terraform/modules/eventbridge/main.tf",
        "kms_key_arn                  = var.kms_key_arn",
    )
    require(
        "terraform/modules/kms/main.tf",
        "AllowEncryptedSNSPublishers",
        'identifiers = ["cloudtrail.amazonaws.com", "cloudwatch.amazonaws.com"]',
    )
    require(
        "terraform/modules/networking/main.tf",
        "map_public_ip_on_launch = false",
    )
    require(
        "terraform/modules/rds_postgres/main.tf",
        "multi_az                            = var.multi_az",
        "deletion_protection                 = var.deletion_protection",
        "iam_database_authentication_enabled = true",
        'value = "1"',
    )
    require(
        "terraform/modules/sqs/main.tf",
        "kms_master_key_id",
        "aws_sqs_queue_redrive_allow_policy",
        "DenyInsecureTransport",
    )
    require(
        "terraform/modules/redis/main.tf",
        "at_rest_encryption_enabled = true",
        "transit_encryption_enabled = true",
        "auth_token                 = random_password.auth.result",
        "automatic_failover_enabled = true",
        "multi_az_enabled           = true",
        'REDIS_URL = "rediss://:',
    )
    require(
        "terraform/modules/backup/main.tf",
        "aws_backup_vault_lock_configuration",
        "cold_storage_after",
        "min_retention_days",
        "kms:GrantIsForAWSResource",
    )
    require(
        "terraform/modules/waf/main.tf",
        "aws_wafv2_web_acl_logging_configuration",
        "redacted_fields",
        "kms_key_id        = aws_kms_key.logging.arn",
    )
    require(
        "terraform/main.tf",
        'module "waf_alb"',
        'resource "aws_wafv2_web_acl_association" "alb"',
        "web_acl_arn  = module.waf_alb.arn",
    )
    require(
        "terraform/global/bootstrap/main.tf",
        "aws_kms_key",
        "aws_s3_bucket_logging",
        "abort_incomplete_multipart_upload",
        "prevent_destroy = true",
        "policy                  = data.aws_iam_policy_document.state_kms.json",
    )
    workflow_path = find_security_workflow()
    if workflow_path is None:
        ERRORS.append(
            "No security workflow found. Set SECURITY_WORKFLOW_PATH or add a workflow "
            "containing validate_security_remediation.py and the blocking Checkov gate."
        )
        workflow_text = ""
    else:
        workflow_text = workflow_path.read_text(encoding="utf-8")
        print(f"Security workflow: {workflow_path.relative_to(ROOT)}")
        require_text(
            workflow_path,
            workflow_text,
            "python scripts/validate_security_remediation.py",
            "--enable-secret-scan-all-files",
            "Enforce complete Checkov policy gate",
            "DEPENDENCY_RESOLUTION_FAILED",
        )

    executable_lines = "\n".join(
        line for line in workflow_text.splitlines() if not line.lstrip().startswith("#")
    )
    if "--soft-fail" in executable_lines:
        ERRORS.append("Security workflow must not use Checkov --soft-fail")
    else:
        PASSES.append("Checkov is configured as a blocking security gate")

    validate_suppressions()
    validate_security_group_egress()

    if ERRORS:
        print("Security remediation validation failed:", file=sys.stderr)
        for error in ERRORS:
            print(f"- {error}", file=sys.stderr)
        print(f"\n{len(PASSES)} checks passed; {len(ERRORS)} checks failed.", file=sys.stderr)
        return 1

    print(f"Security remediation validation passed: {len(PASSES)} checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
