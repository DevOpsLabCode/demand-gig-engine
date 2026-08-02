#!/usr/bin/env python3
"""Validate local Terraform module interfaces without provider downloads.

This lightweight guard complements `terraform validate`. It catches interface drift
before provider initialization: undeclared var references, missing required module
inputs, unknown module arguments, nonexistent module outputs, and invalid HCL string
escapes.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TF = REPO / "terraform"
MODULES = TF / "modules"

BLOCK_RE = re.compile(r'(?m)^\s*(variable|output|module)\s+"([^"]+)"\s*\{')
VAR_REF_RE = re.compile(r"\bvar\.([A-Za-z0-9_]+)\b")
MODULE_OUTPUT_RE = re.compile(r"\bmodule\.([A-Za-z0-9_-]+)\.([A-Za-z0-9_]+)\b")
TOP_LEVEL_ASSIGN_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")
HEREDOC_START_RE = re.compile(r"<<-?\s*([A-Za-z_][A-Za-z0-9_]*)")
INVALID_ESCAPE_RE = re.compile(r'(?<!\\)\\(?![nrt"\\uU])')

MODULE_META_ARGUMENTS = {
    "source",
    "providers",
    "depends_on",
    "count",
    "for_each",
}


@dataclass(frozen=True)
class Block:
    kind: str
    name: str
    body: str
    path: Path


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"(?m)(?<!:)//.*$|#.*$", "", text)


def blocks(path: Path, kinds: set[str] | None = None) -> list[Block]:
    text = path.read_text(encoding="utf-8")
    found: list[Block] = []

    for match in BLOCK_RE.finditer(text):
        kind, name = match.group(1), match.group(2)
        if kinds is not None and kind not in kinds:
            continue

        depth = 1
        quote: str | None = None
        escaped = False
        i = match.end()

        while i < len(text) and depth:
            ch = text[i]

            if quote:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == quote:
                    quote = None
            else:
                if ch in {'"', "'"}:
                    quote = ch
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1

            i += 1

        if depth:
            raise ValueError(f"Unclosed {kind} {name!r} in {path}")

        found.append(Block(kind, name, text[match.end() : i - 1], path))

    return found


def tf_text(directory: Path) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(directory.glob("*.tf"))
    )


def top_level_assignments(text: str) -> set[str]:
    """Return assignments made directly in an HCL block.

    A regex over the complete block body also matches keys nested inside maps
    and objects. For example, only `service_names` is a module argument below;
    `api` and `worker` are map keys:

        service_names = {
          api    = module.backend.service_name
          worker = module.worker.service_name
        }

    This scanner tracks HCL collection nesting, quoted strings, and heredocs so
    only assignments encountered at depth zero are returned.
    """

    names: set[str] = set()
    brace_depth = 0
    bracket_depth = 0
    parenthesis_depth = 0
    quote: str | None = None
    escaped = False
    heredoc_delimiter: str | None = None

    for line in text.splitlines():
        if heredoc_delimiter is not None:
            if line.strip() == heredoc_delimiter:
                heredoc_delimiter = None
            continue

        if (
            quote is None
            and brace_depth == 0
            and bracket_depth == 0
            and parenthesis_depth == 0
        ):
            assignment = TOP_LEVEL_ASSIGN_RE.match(line)
            if assignment:
                names.add(assignment.group(1))

        i = 0
        while i < len(line):
            ch = line[i]

            if quote is not None:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == quote:
                    quote = None
            else:
                if ch in {'"', "'"}:
                    quote = ch
                elif ch == "{":
                    brace_depth += 1
                elif ch == "}":
                    brace_depth = max(0, brace_depth - 1)
                elif ch == "[":
                    bracket_depth += 1
                elif ch == "]":
                    bracket_depth = max(0, bracket_depth - 1)
                elif ch == "(":
                    parenthesis_depth += 1
                elif ch == ")":
                    parenthesis_depth = max(0, parenthesis_depth - 1)

            i += 1

        if quote is None:
            heredoc = HEREDOC_START_RE.search(line)
            if heredoc:
                heredoc_delimiter = heredoc.group(1)

    return names


def module_contract(directory: Path) -> tuple[set[str], set[str], set[str]]:
    variable_blocks: dict[str, Block] = {}
    output_names: set[str] = set()

    for path in sorted(directory.glob("*.tf")):
        for block in blocks(path, {"variable", "output"}):
            if block.kind == "variable":
                variable_blocks[block.name] = block
            else:
                output_names.add(block.name)

    required = {
        name
        for name, block in variable_blocks.items()
        if not re.search(r"(?m)^\s*default\s*=", strip_comments(block.body))
    }

    return set(variable_blocks), required, output_names


def main() -> int:
    errors: list[str] = []
    contracts: dict[str, tuple[set[str], set[str], set[str]]] = {}

    for path in sorted(TF.rglob("*.tf")):
        text = path.read_text(encoding="utf-8")
        for match in INVALID_ESCAPE_RE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            errors.append(
                f"{path.relative_to(REPO)}:{line} contains an invalid HCL "
                "quoted-string escape"
            )

    module_dirs = sorted(path for path in MODULES.iterdir() if path.is_dir())

    for directory in module_dirs:
        declared, required, outputs = module_contract(directory)
        contracts[directory.name] = (declared, required, outputs)

        referenced = set(VAR_REF_RE.findall(strip_comments(tf_text(directory))))
        for name in sorted(referenced - declared):
            errors.append(
                f"{directory.relative_to(REPO)} references undeclared var.{name}"
            )

    root_module_sources: dict[str, str] = {}
    root_text = tf_text(TF)

    for path in sorted(TF.glob("*.tf")):
        for block in blocks(path, {"module"}):
            clean = strip_comments(block.body)
            source_match = re.search(
                r'(?m)^\s*source\s*=\s*"\.\/modules\/([^"]+)"',
                clean,
            )
            if not source_match:
                continue

            source = source_match.group(1)
            root_module_sources[block.name] = source

            if source not in contracts:
                errors.append(
                    f"module.{block.name} references missing local module {source!r}"
                )
                continue

            declared, required, _ = contracts[source]
            supplied = top_level_assignments(clean) - MODULE_META_ARGUMENTS

            for name in sorted(required - supplied):
                errors.append(
                    f"module.{block.name} ({source}) is missing required input {name!r}"
                )

            for name in sorted(supplied - declared):
                errors.append(
                    f"module.{block.name} ({source}) supplies unknown input {name!r}"
                )

    for instance, output in sorted(
        set(MODULE_OUTPUT_RE.findall(strip_comments(root_text)))
    ):
        source = root_module_sources.get(instance)
        if source is None:
            continue

        available = contracts[source][2]
        if output not in available:
            errors.append(
                f"module.{instance}.{output} references missing output "
                f"in modules/{source}"
            )

    if errors:
        print("Terraform module contract validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"Terraform module contracts passed: {len(module_dirs)} modules, "
        f"{len(root_module_sources)} root instances."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
