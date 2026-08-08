#!/usr/bin/env python3
"""Collect CBGB discovery metadata without copying restricted media.

This is the broad-recall companion to collect_open_assets.py. It queries public
metadata/search APIs and stores links/records for later human review. A hit in
this output is NEVER automatically a reconstruction input or a rights grant.

Sources currently queried:
- MusicBrainz events for the CBGB place MBID
- Library of Congress public search API for CBGB / 315 Bowery / 313 Bowery
- Internet Archive advanced-search metadata for CBGB-related records
- Wikidata entity metadata for CBGB (Q1022965)

No image/video/audio bytes are downloaded by this script.
"""

from __future__ import annotations

import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

USER_AGENT = (
    "OpenConcertRealityEvidencePOC/0.2 "
    "(https://github.com/DevOpsLabCode/demand-gig-engine; metadata research)"
)
CBGB_MUSICBRAINZ_PLACE = "011e4ebb-590c-4686-8282-d831a96a903c"
CBGB_WIKIDATA_ID = "Q1022965"


def get_json(url: str, *, timeout: int = 40) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def musicbrainz_events() -> dict:
    events: list[dict] = []
    offset = 0
    limit = 100
    total = None
    while total is None or offset < total:
        params = urllib.parse.urlencode(
            {
                "place": CBGB_MUSICBRAINZ_PLACE,
                "fmt": "json",
                "limit": str(limit),
                "offset": str(offset),
                "inc": "artist-rels",
            }
        )
        url = f"https://musicbrainz.org/ws/2/event?{params}"
        payload = get_json(url)
        total = int(payload.get("event-count", 0))
        batch = payload.get("events", [])
        for event in batch:
            events.append(
                {
                    "id": event.get("id"),
                    "name": event.get("name"),
                    "type": event.get("type"),
                    "time": event.get("time"),
                    "begin_time": event.get("begin-time"),
                    "end_time": event.get("end-time"),
                    "life_span": event.get("life-span", {}),
                    "relations": event.get("relations", []),
                    "source_url": f"https://musicbrainz.org/event/{event.get('id')}",
                    "rights_class": "C_METADATA_VERIFY_DATASET_LICENSE",
                    "research_status": "unverified_discovery",
                }
            )
        offset += len(batch)
        if not batch:
            break
        time.sleep(1.1)  # MusicBrainz asks clients to stay at roughly one request/second.
    return {
        "place_mbid": CBGB_MUSICBRAINZ_PLACE,
        "reported_total": total or 0,
        "collected": len(events),
        "events": events,
    }


def loc_search() -> dict:
    queries = ["CBGB", '"315 Bowery"', '"313 Bowery"', '"Palace Hotel" Bowery']
    results: list[dict] = []
    seen: set[str] = set()
    for query in queries:
        params = urllib.parse.urlencode({"q": query, "fo": "json", "c": "100"})
        payload = get_json(f"https://www.loc.gov/search/?{params}")
        for item in payload.get("results", []):
            item_id = str(item.get("id") or item.get("url") or item.get("title"))
            if item_id in seen:
                continue
            seen.add(item_id)
            results.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "date": item.get("date"),
                    "url": item.get("url"),
                    "original_format": item.get("original_format"),
                    "partof": item.get("partof"),
                    "subjects": item.get("subject"),
                    "query_that_found_it": query,
                    "rights_class": "D_UNTIL_ITEM_RIGHTS_REVIEW",
                    "research_status": "unverified_discovery",
                }
            )
        time.sleep(0.2)
    return {"queries": queries, "collected": len(results), "records": results}


def internet_archive_search() -> dict:
    query = '(title:CBGB OR subject:CBGB OR description:"CBGB" OR description:"315 Bowery")'
    fields = [
        "identifier",
        "title",
        "creator",
        "date",
        "description",
        "mediatype",
        "rights",
        "licenseurl",
        "subject",
    ]
    rows = 500
    params = urllib.parse.urlencode(
        {
            "q": query,
            "fl[]": fields,
            "rows": str(rows),
            "page": "1",
            "output": "json",
        },
        doseq=True,
    )
    payload = get_json(f"https://archive.org/advancedsearch.php?{params}")
    docs = payload.get("response", {}).get("docs", [])
    records = []
    for doc in docs:
        identifier = doc.get("identifier")
        records.append(
            {
                **doc,
                "source_url": f"https://archive.org/details/{identifier}" if identifier else None,
                "rights_class": "D_UNTIL_ITEM_RIGHTS_REVIEW",
                "research_status": "unverified_discovery",
            }
        )
    return {
        "query": query,
        "reported_total": payload.get("response", {}).get("numFound", 0),
        "collected": len(records),
        "records": records,
    }


def wikidata_entity() -> dict:
    url = (
        "https://www.wikidata.org/wiki/Special:EntityData/"
        f"{CBGB_WIKIDATA_ID}.json"
    )
    payload = get_json(url)
    entity = payload.get("entities", {}).get(CBGB_WIKIDATA_ID, {})
    return {
        "id": CBGB_WIKIDATA_ID,
        "source_url": f"https://www.wikidata.org/wiki/{CBGB_WIKIDATA_ID}",
        "labels": entity.get("labels", {}),
        "descriptions": entity.get("descriptions", {}),
        "aliases": entity.get("aliases", {}),
        "claims": entity.get("claims", {}),
        "rights_class": "C_METADATA_VERIFY_CC0_SCOPE",
        "research_status": "raw_discovery",
    }


def run_source(name: str, func) -> dict:
    print(f"Collecting {name} metadata...")
    try:
        return {"status": "ok", "data": func()}
    except Exception as exc:  # keep one source failure from destroying the whole crawl
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    destination = pathlib.Path(
        sys.argv[1] if len(sys.argv) > 1 else "discovered-public-metadata.json"
    )
    output = {
        "collector": "Open Concert Reality Evidence POC",
        "version": "0.2",
        "subject": "CBGB & OMFUG / 313-315 Bowery",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": (
            "Discovery metadata is not a rights grant. Do not download, train on or redistribute "
            "linked media until the exact item rights and intended use have been reviewed."
        ),
        "sources": {
            "musicbrainz": run_source("MusicBrainz", musicbrainz_events),
            "library_of_congress": run_source("Library of Congress", loc_search),
            "internet_archive": run_source("Internet Archive", internet_archive_search),
            "wikidata": run_source("Wikidata", wikidata_entity),
        },
    }
    destination.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved metadata discovery report to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
