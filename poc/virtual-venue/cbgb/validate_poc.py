#!/usr/bin/env python3
"""Validate the CBGB POC evidence pack for basic provenance/integrity errors."""

from __future__ import annotations

import csv
import json
import pathlib
import sys
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parent
VALID_RIGHTS = {"A", "B", "C", "D", "E"}


def load_json(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_confidences(value, path: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if "confidence" in key.lower() and isinstance(child, (int, float)):
                if not 0 <= child <= 1:
                    fail(errors, f"{child_path}: confidence {child!r} is outside 0..1")
            validate_confidences(child, child_path, errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_confidences(child, f"{path}[{index}]", errors)


def main() -> int:
    errors: list[str] = []

    evidence = load_json("evidence.json")
    geometry = load_json("geometry.json")
    reference = load_json("reference_catalog_seed.json")

    rights_classes = set(evidence.get("rights_classes", {}))
    if rights_classes != VALID_RIGHTS:
        fail(errors, f"evidence.json rights classes are {sorted(rights_classes)}, expected {sorted(VALID_RIGHTS)}")

    source_groups = evidence.get("source_groups", [])
    source_ids = [entry.get("id") for entry in source_groups]
    if None in source_ids:
        fail(errors, "evidence.json contains a source without id")
    if len(source_ids) != len(set(source_ids)):
        fail(errors, "evidence.json contains duplicate source ids")

    for index, source in enumerate(source_groups):
        rights = source.get("rights_class")
        if rights not in VALID_RIGHTS:
            fail(errors, f"source_groups[{index}] {source.get('id')}: invalid rights_class {rights!r}")
        url = source.get("url")
        if url and not valid_url(url):
            fail(errors, f"source_groups[{index}] {source.get('id')}: invalid URL {url!r}")

    timeline_path = ROOT / "timeline_seed.csv"
    with timeline_path.open(newline="", encoding="utf-8") as handle:
        timeline = list(csv.DictReader(handle))
    for line, row in enumerate(timeline, start=2):
        source_id = row.get("source_id", "")
        if source_id and source_id not in source_ids:
            fail(errors, f"timeline_seed.csv:{line}: unknown source_id {source_id!r}")
        rights = row.get("rights_class", "")
        if rights and rights not in VALID_RIGHTS:
            fail(errors, f"timeline_seed.csv:{line}: invalid rights_class {rights!r}")
        try:
            confidence = float(row.get("confidence", ""))
            if not 0 <= confidence <= 1:
                raise ValueError
        except ValueError:
            fail(errors, f"timeline_seed.csv:{line}: invalid confidence {row.get('confidence')!r}")

    validate_confidences(geometry, "geometry", errors)
    validate_confidences(reference, "reference_catalog_seed", errors)

    footprint = geometry.get("historic_tenant_footprint", {})
    if footprint.get("status") != "UNSOLVED":
        fail(errors, "historic tenant footprint must remain UNSOLVED until a survey/plan/camera solve supports it")
    if footprint.get("former_estimate_disposition") != "deprecated_as_geometry_fact":
        fail(errors, "old 25x75 estimate must remain explicitly deprecated")

    current_tenant = evidence.get("source_groups", [])
    if not any(source.get("id") == "john-varvatos-bowery-current" for source in current_tenant):
        fail(errors, "current-survey outreach source is missing")
    if not any(source.get("id") == "kersavage-reaven-2006" for source in source_groups):
        fail(errors, "Priority-0 Kersavage/Reaven source lead is missing")
    if not any(source.get("id") == "nyu-nightclubbing-mss305" for source in source_groups):
        fail(errors, "NYU NIGHTCLUBBING archive source is missing")

    if errors:
        print("CBGB POC validation FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "CBGB POC validation passed: "
        f"{len(source_groups)} source groups, {len(timeline)} timeline rows, "
        "JSON/CSV provenance checks OK."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
