#!/usr/bin/env python3
"""Offline Terraform lexical and root/module interface validation.

This does not replace `terraform validate`; it catches malformed delimiters,
unknown module arguments, missing required module inputs, and references to
undeclared child-module outputs before provider installation is available.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "terraform"

BLOCK_START = re.compile(r'\b(?P<kind>module|variable|output)\s+"(?P<name>[^"]+)"\s*\{')
ASSIGNMENT = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=')
MODULE_REF = re.compile(r'\bmodule\.([A-Za-z0-9_-]+)\.([A-Za-z0-9_]+)\b')


def matching_brace(text: str, opening: int) -> int:
    depth = 0
    quote = False
    escape = False
    line_comment = False
    block_comment = False
    i = opening
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if line_comment:
            if ch == "\n":
                line_comment = False
            i += 1
            continue
        if block_comment:
            if ch == "*" and nxt == "/":
                block_comment = False
                i += 2
            else:
                i += 1
            continue
        if quote:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                quote = False
            i += 1
            continue
        if ch == "#" or (ch == "/" and nxt == "/"):
            line_comment = True
            i += 2 if ch == "/" else 1
            continue
        if ch == "/" and nxt == "*":
            block_comment = True
            i += 2
            continue
        if ch == '"':
            quote = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
            if depth < 0:
                raise ValueError(f"unexpected closing brace at byte {i}")
        i += 1
    raise ValueError(f"unclosed block starting at byte {opening}")


def blocks(text: str, kind: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in BLOCK_START.finditer(text):
        if match.group("kind") != kind:
            continue
        name = match.group("name")
        opening = text.find("{", match.start())
        closing = matching_brace(text, opening)
        if name in result:
            raise ValueError(f"duplicate {kind} block {name}")
        result[name] = text[opening + 1 : closing]
    return result


def top_level_assignments(body: str) -> set[str]:
    keys: set[str] = set()
    depth = 0
    quote = False
    escape = False
    for line in body.splitlines():
        if depth == 0:
            match = ASSIGNMENT.match(line)
            if match:
                keys.add(match.group(1))
        for ch in line:
            if quote:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    quote = False
                continue
            if ch == '"':
                quote = True
            elif ch in "{[(":
                depth += 1
            elif ch in "}])":
                depth -= 1
                if depth < 0:
                    raise ValueError("unbalanced delimiter in block")
    if depth != 0 or quote:
        raise ValueError("unbalanced delimiter or string in block")
    return keys


def lexical_check(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    # Every resource/module/data/etc. brace is exercised by walking the file.
    stack: list[str] = []
    pairs = {"}": "{", "]": "[", ")": "("}
    quote = False
    escape = False
    line_comment = False
    block_comment = False
    i = 0
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if line_comment:
            line_comment = ch != "\n"
            i += 1
            continue
        if block_comment:
            if ch == "*" and nxt == "/":
                block_comment = False
                i += 2
            else:
                i += 1
            continue
        if quote:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                quote = False
            i += 1
            continue
        if ch == "#" or (ch == "/" and nxt == "/"):
            line_comment = True
            i += 2 if ch == "/" else 1
            continue
        if ch == "/" and nxt == "*":
            block_comment = True
            i += 2
            continue
        if ch == '"':
            quote = True
        elif ch in "{[(":
            stack.append(ch)
        elif ch in "}])":
            if not stack or stack.pop() != pairs[ch]:
                raise ValueError(f"mismatched {ch} at byte {i}")
        i += 1
    if quote or block_comment or stack:
        raise ValueError(f"unterminated string/comment/delimiters: {stack}")


def main() -> int:
    errors: list[str] = []
    tf_files = sorted(TF.rglob("*.tf"))
    for path in tf_files:
        try:
            lexical_check(path)
        except ValueError as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")

    root_text = "\n".join(path.read_text(encoding="utf-8") for path in sorted(TF.glob("*.tf")))
    try:
        root_modules = blocks(root_text, "module")
    except ValueError as exc:
        errors.append(f"terraform root modules: {exc}")
        root_modules = {}

    module_sources: dict[str, Path] = {}
    meta_arguments = {"source", "version", "providers", "depends_on", "count", "for_each"}
    for module_name, body in root_modules.items():
        source_match = re.search(r'(?m)^\s*source\s*=\s*"([^"]+)"', body)
        if not source_match:
            errors.append(f"module.{module_name}: missing source")
            continue
        source = source_match.group(1)
        if not source.startswith("./modules/"):
            continue
        module_path = (TF / source).resolve()
        module_sources[module_name] = module_path
        variable_text = "\n".join(p.read_text(encoding="utf-8") for p in sorted(module_path.glob("*.tf")))
        try:
            variable_blocks = blocks(variable_text, "variable")
        except ValueError as exc:
            errors.append(f"module.{module_name}: {exc}")
            continue
        declared = set(variable_blocks)
        required = {
            name
            for name, variable_body in variable_blocks.items()
            if not re.search(r'(?m)^\s*default\s*=', variable_body)
        }
        try:
            supplied = top_level_assignments(body) - meta_arguments
        except ValueError as exc:
            errors.append(f"module.{module_name}: {exc}")
            continue
        unknown = supplied - declared
        missing = required - supplied
        if unknown:
            errors.append(f"module.{module_name}: unknown inputs {sorted(unknown)}")
        if missing:
            errors.append(f"module.{module_name}: missing required inputs {sorted(missing)}")

    for module_name, output_name in sorted(set(MODULE_REF.findall(root_text))):
        module_path = module_sources.get(module_name)
        if module_path is None:
            errors.append(f"reference module.{module_name}.{output_name}: module is not locally declared")
            continue
        output_text = "\n".join(p.read_text(encoding="utf-8") for p in sorted(module_path.glob("*.tf")))
        try:
            declared_outputs = set(blocks(output_text, "output"))
        except ValueError as exc:
            errors.append(f"module.{module_name} outputs: {exc}")
            continue
        if output_name not in declared_outputs:
            errors.append(f"module.{module_name}.{output_name}: output is not declared")

    if errors:
        print("Terraform contract validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"Validated {len(tf_files)} Terraform files, "
        f"{len(root_modules)} root module instances, and all local module interfaces."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
