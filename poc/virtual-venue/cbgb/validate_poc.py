#!/usr/bin/env python3
"""Validate the CBGB POC evidence pack for provenance/integrity errors."""

from __future__ import annotations

import csv
import json
import pathlib
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parent
VALID_RIGHTS = {"A", "B", "C", "D", "E"}
REQUIRED_FILES = {
    "evidence.json",
    "geometry.json",
    "reference_catalog_seed.json",
    "audio_archive_seed.json",
    "research_leads.json",
    "timeline_seed.csv",
    "RIGHTS_ACQUISITION_QUEUE.csv",
    "CAPTURE_GAPS.md",
    "FOOTPRINT_RESEARCH.md",
    "EVIDENCE_GRAPH.md",
    "collect_open_assets.py",
    "collect_public_metadata.py",
    "collect_nyu_fales_metadata.py",
}


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


def validate_rights_value(value: str | None, path: str, errors: list[str]) -> None:
    if value not in VALID_RIGHTS:
        fail(errors, f"{path}: invalid rights_class {value!r}")


def main() -> int:
    errors: list[str] = []

    missing = sorted(name for name in REQUIRED_FILES if not (ROOT / name).exists())
    if missing:
        fail(errors, f"required POC files are missing: {', '.join(missing)}")

    evidence = load_json("evidence.json")
    geometry = load_json("geometry.json")
    reference = load_json("reference_catalog_seed.json")
    audio = load_json("audio_archive_seed.json")
    research_leads = load_json("research_leads.json")

    rights_classes = set(evidence.get("rights_classes", {}))
    if rights_classes != VALID_RIGHTS:
        fail(
            errors,
            f"evidence.json rights classes are {sorted(rights_classes)}, expected {sorted(VALID_RIGHTS)}",
        )

    source_groups = evidence.get("source_groups", [])
    source_ids = [entry.get("id") for entry in source_groups]
    if None in source_ids:
        fail(errors, "evidence.json contains a source without id")
    if len(source_ids) != len(set(source_ids)):
        fail(errors, "evidence.json contains duplicate source ids")

    for index, source in enumerate(source_groups):
        validate_rights_value(
            source.get("rights_class"),
            f"source_groups[{index}] {source.get('id')}",
            errors,
        )
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
        if rights:
            validate_rights_value(rights, f"timeline_seed.csv:{line}", errors)
        try:
            confidence = float(row.get("confidence", ""))
            if not 0 <= confidence <= 1:
                raise ValueError
        except ValueError:
            fail(errors, f"timeline_seed.csv:{line}: invalid confidence {row.get('confidence')!r}")

    leads = research_leads.get("leads", [])
    lead_ids = [entry.get("id") for entry in leads]
    if None in lead_ids:
        fail(errors, "research_leads.json contains a lead without id")
    if len(lead_ids) != len(set(lead_ids)):
        fail(errors, "research_leads.json contains duplicate lead ids")
    for index, lead in enumerate(leads):
        validate_rights_value(
            lead.get("rights_class"),
            f"research_leads.leads[{index}] {lead.get('id')}",
            errors,
        )
        url = lead.get("url")
        if url and not valid_url(url):
            fail(errors, f"research_leads.leads[{index}] {lead.get('id')}: invalid URL {url!r}")

    archives = audio.get("archives", [])
    for index, archive in enumerate(archives):
        validate_rights_value(
            archive.get("rights_class"),
            f"audio_archive_seed.archives[{index}] {archive.get('archive')}",
            errors,
        )
        url = archive.get("url")
        if url and not valid_url(url):
            fail(errors, f"audio_archive_seed.archives[{index}]: invalid URL {url!r}")
        media_ids = [item.get("media_id") for item in archive.get("cbgb_items", [])]
        if None in media_ids:
            fail(errors, f"audio_archive_seed.archives[{index}] contains an item without media_id")
        if len(media_ids) != len(set(media_ids)):
            fail(errors, f"audio_archive_seed.archives[{index}] contains duplicate media IDs")

    validate_confidences(geometry, "geometry", errors)
    validate_confidences(reference, "reference_catalog_seed", errors)
    validate_confidences(audio, "audio_archive_seed", errors)
    validate_confidences(research_leads, "research_leads", errors)

    footprint = geometry.get("historic_tenant_footprint", {})
    if footprint.get("status") != "UNSOLVED":
        fail(
            errors,
            "historic tenant footprint must remain UNSOLVED until a survey/plan/camera solve supports it",
        )
    if footprint.get("former_estimate_disposition") != "deprecated_as_geometry_fact":
        fail(errors, "old 25x75 estimate must remain explicitly deprecated")

    critical_source_ids = {
        "john-varvatos-bowery-current",
        "kersavage-reaven-2006",
        "nyu-nightclubbing-mss305",
        "nrhp-bowery",
        "nyc-ll97-building-list",
    }
    missing_sources = sorted(critical_source_ids - set(source_ids))
    if missing_sources:
        fail(errors, f"critical source groups are missing: {', '.join(missing_sources)}")

    if errors:
        print("CBGB POC validation FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "CBGB POC validation passed: "
        f"{len(source_groups)} source groups, {len(timeline)} timeline rows, "
        f"{len(leads)} research leads, {sum(len(a.get('cbgb_items', [])) for a in archives)} audio references; "
        "JSON/CSV provenance checks OK."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
