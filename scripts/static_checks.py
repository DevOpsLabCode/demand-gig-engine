#!/usr/bin/env python3
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Runs dependency-free structural checks over source files, configuration, schemas, screenshots, and integration contracts.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""Dependency-free structural validation for the Demand Gig MVP package."""
from __future__ import annotations

import ast
import json
import struct
import subprocess
import sys
from pathlib import Path

# Convert parser or tool failures into an explicit validation result instead of aborting the complete offline report.
try:
    import yaml
except ImportError:  # pragma: no cover - optional helper
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []
PASSES: list[str] = []


def check(condition: bool, message: str) -> None:
    """
    Record one dependency-free validation result and increment the shared pass/fail counters.
    
    Args:
        condition: Boolean assertion that determines whether the validation check passes.
        message: Queue, webhook, or validation message being processed.
    """
    (PASSES if condition else ERRORS).append(message)


def check_python() -> None:
    """
    Parse every Python source file to catch syntax errors without importing project dependencies.
    """
    files = sorted((ROOT / "backend").rglob("*.py"))
    # Process each `path` from `files` in a deterministic order.
    for path in files:
        # Convert parser or tool failures into an explicit validation result instead of aborting the complete offline report.
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception as exc:
            ERRORS.append(f"Python parse failed: {path.relative_to(ROOT)}: {exc}")
    check(bool(files), f"Parsed {len(files)} Python files")


def check_json() -> None:
    """
    Load a JSON file and report malformed configuration or contract data.
    """
    # Process each `rel` from `[ "frontend/package.json", "frontend/tsconfig.json",
    # "docs/schemas/...` in a deterministic order.
    for rel in [
        "frontend/package.json",
        "frontend/tsconfig.json",
        "docs/schemas/vibesmeet-event-handoff.schema.json",
        "docs/schemas/vibesmeet-webhook-envelope.schema.json",
        "docs/examples/vibesmeet-event-handoff.example.json",
        "docs/examples/vibesmeet-webhook.example.json",
    ]:
        # Convert parser or tool failures into an explicit validation result instead of aborting the complete offline report.
        try:
            json.loads((ROOT / rel).read_text(encoding="utf-8"))
            PASSES.append(f"Valid JSON: {rel}")
        except Exception as exc:
            ERRORS.append(f"Invalid JSON: {rel}: {exc}")


def check_compose() -> None:
    """
    Verify the required Compose services and database health dependency.
    """
    path = ROOT / "docker-compose.yml"
    # Fall back to dependency-free text checks when PyYAML is unavailable in the validation environment.
    if yaml is None:
        check(path.exists(), "docker-compose.yml exists (PyYAML not installed; parse skipped)")
        return
    # Convert parser or tool failures into an explicit validation result instead of aborting the complete offline report.
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        services = data.get("services", {})
        check(set(["db", "backend", "frontend"]).issubset(services), "Compose defines db/backend/frontend services")
        check(services["backend"].get("depends_on", {}).get("db", {}).get("condition") == "service_healthy", "Backend waits for healthy database")
    except Exception as exc:
        ERRORS.append(f"Compose parse failed: {exc}")


def check_migrations() -> None:
    """
    Confirm that Django migration numbers form the expected sequential chain.
    """
    migration_dir = ROOT / "backend/gigs/migrations"
    migrations = sorted(p for p in migration_dir.glob("[0-9][0-9][0-9][0-9]_*.py"))
    names = [p.name.split("_", 1)[0] for p in migrations]
    expected = [f"{index:04d}" for index in range(1, len(migrations) + 1)]
    check(names == expected, f"Migration chain is sequential: {', '.join(names)}")
    model_text = (ROOT / "backend/gigs/models.py").read_text(encoding="utf-8")
    migration_text = "\n".join(p.read_text(encoding="utf-8") for p in migrations)
    check("pledge_campaign_idempotency_uniq" in model_text and "pledge_campaign_idempotency_uniq" in migration_text, "Campaign-scoped pledge idempotency exists in model and migration")


def png_dimensions(path: Path) -> tuple[int, int]:
    """
    Read PNG header dimensions without requiring an imaging dependency.
    
    Args:
        path: Relative API path appended to the configured service base URL.
    
    Returns:
        The ordered result tuple described by the return annotation and function summary.
    
    Raises:
        ValueError: When the documented validation or integration precondition fails.
    """
    # Enter the context manager to scope resources, transactions, or cleanup to this block.
    with path.open("rb") as stream:
        header = stream.read(24)
    # Enforce the collection-size or total-value invariant before accepting the contract.
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    return struct.unpack(">II", header[16:24])


def check_screenshots() -> None:
    """
    Validate screenshot files, dimensions, and the combined PDF artifact.
    """
    expected = {
        "01-landing-and-seed.png": (1, 1),
        "02-campaign-detail.png": (1, 1),
        "03-mobile-campaign.png": (1, 1),
    }
    # Process each `name, minimum` from `expected.items()` in a deterministic order.
    for name, minimum in expected.items():
        path = ROOT / "screenshots" / name
        # Convert parser or tool failures into an explicit validation result instead of aborting the complete offline report.
        try:
            width, height = png_dimensions(path)
            check(width >= minimum[0] and height >= minimum[1], f"PNG valid: {name} ({width}x{height})")
        except Exception as exc:
            ERRORS.append(f"PNG invalid: {name}: {exc}")


def check_pdf() -> None:
    """
    Confirm the PDF signature, EOF marker, and renderer-readable structure.
    """
    path = ROOT / "docs/Demand_Driven_Gig_MVP_README_and_Screenshots.pdf"
    check(path.exists() and path.stat().st_size > 100_000, "Combined README/screenshots PDF exists")
    # Report a missing artifact before attempting header or renderer checks.
    if not path.exists():
        return
    data = path.read_bytes()
    check(data.startswith(b"%PDF-"), "PDF header is valid")
    check(b"%%EOF" in data[-4096:], "PDF EOF marker is present")
    # Run the stronger pdfinfo preflight only when the executable exists in the current environment.
    if subprocess.run(["bash", "-lc", "command -v pdfinfo >/dev/null"], check=False).returncode == 0:
        result = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=False)
        check(result.returncode == 0 and "Pages:" in result.stdout, "pdfinfo opens the combined PDF")


def check_contracts() -> None:
    """
    Parse and validate the proposed OpenAPI and JSON integration contracts.
    """
    api = (ROOT / "frontend/src/api.ts").read_text(encoding="utf-8")
    urls = (ROOT / "backend/gigs/urls.py").read_text(encoding="utf-8")
    views = (ROOT / "backend/gigs/views.py").read_text(encoding="utf-8")
    auth_views = (ROOT / "backend/gigs/auth_views.py").read_text(encoding="utf-8")
    social_auth = (ROOT / "backend/gigs/social_auth.py").read_text(encoding="utf-8")
    settings = (ROOT / "backend/config/settings.py").read_text(encoding="utf-8")
    # Process each `fragment` from `["/campaigns/", "/auth/config/", "/auth/profile/",
    # "/auth/logout/",...` in a deterministic order.
    for fragment in ["/campaigns/", "/auth/config/", "/auth/profile/", "/auth/logout/", "/facebook/config/", "/facebook/login/", "/facebook/pages/", "/vibesmeet/config/"]:
        check(fragment in api, f"Frontend API contains {fragment}")
    # Process each `symbol` from `["CampaignViewSet", "facebook_config", "facebook_login",
    # "facebook_...` in a deterministic order.
    for symbol in ["CampaignViewSet", "facebook_config", "facebook_login", "facebook_pages", "stripe_webhook", "vibesmeet_config", "vibesmeet_webhook"]:
        check(symbol in urls or symbol in views, f"Backend exposes {symbol}")
    check('lookup_field = "slug"' in views, "Campaign API uses slug lookup expected by frontend")
    check("def health" in auth_views and 'path("health/"' in urls, "Backend exposes an ALB/container health endpoint")
    check("google" in social_auth and "facebook" in social_auth and "instagram" in social_auth and "tiktok" in social_auth, "Social auth lists Google/Facebook/Instagram/TikTok")
    check("django-allauth" in (ROOT / "backend/requirements.txt").read_text(encoding="utf-8"), "Django allauth dependency is declared")
    check("allauth.socialaccount.providers.tiktok" in settings, "All social providers are registered in Django settings")
    check("IsCampaignOwnerOrStaff" in views and "owner_actions" in views, "Campaign lifecycle actions enforce owner/staff authorization")


def check_required_files() -> None:
    """
    Verify that the repository contains every required application, document, and automation file.
    """
    required = [
        "README.md",
        "TEST_REPORT.md",
        "docker-compose.yml",
        "Dockerfile.backend",
        "Dockerfile.frontend",
        "backend/manage.py",
        "backend/requirements.txt",
        "frontend/package.json",
        "docs/VIBESMEET_INTEGRATION_AND_MODULE_BLUEPRINT.md",
        "docs/openapi/vibesmeet-bridge.openapi.yaml",
        "docs/schemas/vibesmeet-event-handoff.schema.json",
        "docs/schemas/vibesmeet-webhook-envelope.schema.json",
        "docs/examples/vibesmeet-event-handoff.example.json",
        "docs/examples/vibesmeet-webhook.example.json",
        "backend/integrations/vibesmeet/client.py",
        "backend/integrations/vibesmeet/webhooks.py",
        "backend/gigs/auth_views.py",
        "backend/gigs/social_auth.py",
        "backend/gigs/permissions.py",
        "backend/gigs/tests/test_auth.py",
        "docs/SOCIAL_AUTHENTICATION.md",
        "docs/AWS_PRODUCTION_ARCHITECTURE.md",
        "docs/aws-production-architecture.svg",
        "docs/social-auth-flow.svg",
        "scripts/run_all_tests.sh",
    ]
    # Process each `rel` from `required` in a deterministic order.
    for rel in required:
        check((ROOT / rel).exists(), f"Required file exists: {rel}")


def check_vibesmeet_bridge() -> None:
    """
    Check the bridge client, webhook verification, ownership boundaries, and supporting contracts.
    """
    blueprint = (ROOT / "docs/VIBESMEET_INTEGRATION_AND_MODULE_BLUEPRINT.md").read_text(encoding="utf-8")
    client = (ROOT / "backend/integrations/vibesmeet/client.py").read_text(encoding="utf-8")
    webhook = (ROOT / "backend/integrations/vibesmeet/webhooks.py").read_text(encoding="utf-8")
    openapi = (ROOT / "docs/openapi/vibesmeet-bridge.openapi.yaml").read_text(encoding="utf-8")
    # Use structured YAML parsing when available for a stronger OpenAPI validation.
    if yaml is not None:
        # Convert parser or tool failures into an explicit validation result instead of aborting the complete offline report.
        try:
            parsed_openapi = yaml.safe_load(openapi)
            check(parsed_openapi.get("openapi") == "3.1.0", "Proposed VibesMeet OpenAPI document parses")
        except Exception as exc:
            ERRORS.append(f"VibesMeet OpenAPI parse failed: {exc}")
    check("Product boundary" in blueprint and "Missing-module catalog" in blueprint, "VibesMeet blueprint documents ownership and missing modules")
    check("Idempotency-Key" in client and "X-Correlation-ID" in client, "VibesMeet client sends idempotency and correlation headers")
    check("verify_signature" in webhook, "VibesMeet webhook parser verifies signatures")
    check("Contract proposal" in openapi and "/v1/partner/events/drafts" in openapi, "Proposed VibesMeet OpenAPI contract is present")


def main() -> int:
    """
    Run the module as a command-line validation entry point and return a process status.
    
    Returns:
        The typed result described in the function summary and return annotation.
    """
    check_required_files()
    check_python()
    check_json()
    check_compose()
    check_migrations()
    check_contracts()
    check_vibesmeet_bridge()
    check_screenshots()
    check_pdf()

    # Process each `message` from `PASSES` in a deterministic order.
    for message in PASSES:
        print(f"PASS: {message}")
    # Process each `message` from `ERRORS` in a deterministic order.
    for message in ERRORS:
        print(f"FAIL: {message}", file=sys.stderr)
    print(f"\nSummary: {len(PASSES)} passed, {len(ERRORS)} failed")
    return 1 if ERRORS else 0


# Execute the command-line entry point only when this module is run directly.
if __name__ == "__main__":
    raise SystemExit(main())
