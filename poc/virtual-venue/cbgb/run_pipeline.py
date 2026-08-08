#!/usr/bin/env python3
"""Run the CBGB historical-twin POC as one automated pipeline.

The process is automated end-to-end, but it deliberately stops at policy gates
that cannot safely be inferred by software: rights approval and publication
approval. Those gates are explicit command-line inputs so the pipeline itself
remains deterministic and auditable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent
STAGES = [
    ("validate_seed", [sys.executable, "validate_poc.py"]),
    ("collect_commons", [sys.executable, "collect_open_assets.py", "open-assets"]),
    (
        "collect_public_metadata",
        [sys.executable, "collect_public_metadata.py", "discovered-public-metadata.json"],
    ),
    (
        "collect_nyu_metadata",
        [sys.executable, "collect_nyu_fales_metadata.py", "nyu-fales-cbgb-metadata.json"],
    ),
    ("validate_final", [sys.executable, "validate_poc.py"]),
]


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(stage: str, command: list[str], dry_run: bool = False) -> dict:
    print(f"== {stage} ==")
    if dry_run:
        return {"stage": stage, "status": "dry_run", "command": command}

    process = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(process.stdout, end="")
    if process.stderr:
        print(process.stderr, file=sys.stderr, end="")
    return {
        "stage": stage,
        "status": "ok" if process.returncode == 0 else "failed",
        "returncode": process.returncode,
        "command": command,
        "stdout_tail": process.stdout[-4000:],
        "stderr_tail": process.stderr[-4000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Automate the CBGB historical-twin POC")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--capture",
        help="Optional permissioned capture video or image directory for reconstruction",
    )
    parser.add_argument("--work-dir", default="work/cbgb-2006-closing")
    parser.add_argument(
        "--approved-rights",
        action="store_true",
        help="Operator confirms reconstruction inputs passed rights review",
    )
    parser.add_argument(
        "--approved-publish",
        action="store_true",
        help="Operator authorizes publication of generated artifacts",
    )
    args = parser.parse_args()

    state = {
        "pipeline": "cbgb-historical-twin",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "stages": [],
        "gates": {
            "rights_approved": args.approved_rights,
            "publish_approved": args.approved_publish,
        },
    }

    for name, command in STAGES:
        result = run(name, command, args.dry_run)
        state["stages"].append(result)
        if result["status"] == "failed":
            break

    successful_so_far = all(
        result["status"] in {"ok", "dry_run"} for result in state["stages"]
    )

    if args.capture and successful_so_far:
        if not args.approved_rights:
            state["stages"].append(
                {
                    "stage": "reconstruct",
                    "status": "blocked",
                    "reason": "--approved-rights is required before capture/media is consumed by reconstruction",
                }
            )
        else:
            reconstruct_command = [
                "../reconstruct.sh",
                args.capture,
                args.work_dir,
            ]
            state["stages"].append(run("reconstruct", reconstruct_command, args.dry_run))

    if args.approved_publish:
        if not args.approved_rights:
            state["stages"].append(
                {
                    "stage": "publish",
                    "status": "blocked",
                    "reason": "publish cannot proceed without rights approval",
                }
            )
        elif not args.capture:
            state["stages"].append(
                {
                    "stage": "publish",
                    "status": "blocked",
                    "reason": "no capture/reconstructed asset was supplied",
                }
            )
        else:
            state["stages"].append(
                {
                    "stage": "publish",
                    "status": "ready_for_external_publisher",
                    "reason": "POC intentionally does not modify production hosting or main branch",
                }
            )

    for name in [
        "evidence.json",
        "geometry.json",
        "timeline_seed.csv",
        "reference_catalog_seed.json",
        "audio_archive_seed.json",
        "research_leads.json",
    ]:
        path = ROOT / name
        if path.exists():
            state.setdefault("inputs", {})[name] = {
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }

    state["finished_at"] = datetime.now(timezone.utc).isoformat()
    output = ROOT / "pipeline-run.json"
    output.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"Wrote {output}")

    return 1 if any(stage.get("status") == "failed" for stage in state["stages"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
