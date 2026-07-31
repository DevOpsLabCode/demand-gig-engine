#!/usr/bin/env python3
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Validates repository-local Markdown links without network access.

"""Fail when a Markdown document links to a missing local file or directory."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#", "data:")


def main() -> int:
    errors: list[str] = []
    checked = 0
    documents = sorted(
        path for path in ROOT.rglob("*.md")
        if not any(part in {".git", ".terraform", "node_modules", ".venv"} for part in path.parts)
    )
    for document in documents:
        text = document.read_text(encoding="utf-8")
        for match in LINK.finditer(text):
            target = match.group(1).strip()
            # Optional Markdown titles follow the destination after whitespace.
            if target.startswith("<") and ">" in target:
                target = target[1:target.index(">")]
            else:
                target = target.split(maxsplit=1)[0]
            if not target or target.startswith(SKIP_PREFIXES):
                continue
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not target:
                continue
            checked += 1
            resolved = (document.parent / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"{document.relative_to(ROOT)}: local link escapes repository: {target}")
                continue
            if not resolved.exists():
                line = text.count("\n", 0, match.start()) + 1
                errors.append(f"{document.relative_to(ROOT)}:{line}: missing local target {target}")

    if errors:
        print("Documentation-link validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Validated {checked} local links across {len(documents)} Markdown files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
