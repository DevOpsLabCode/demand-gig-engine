#!/usr/bin/env python3
"""Harvest CBGB metadata occurrences from public NYU Fales finding aids.

This script deliberately downloads only finding-aid HTML/text metadata. It does
NOT download archival audio, video, images, PDFs, access copies, or restricted
media. Matching text blocks are saved for research review and catalog-ID
resolution.

Collections seeded here:
- MSS.213 Peter Dougherty Collection
- MSS.305 NIGHTCLUBBING Archive by Pat Ivers and Emily Armstrong

A finding-aid hit is a research lead, not a grant to reproduce the underlying
archival material.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

USER_AGENT = (
    "OpenConcertRealityEvidencePOC/0.3 "
    "(https://github.com/DevOpsLabCode/demand-gig-engine; metadata research)"
)
SOURCES = [
    {
        "id": "nyu-fales-mss213",
        "collection": "Peter Dougherty Collection",
        "call_number": "MSS.213",
        "url": "https://findingaids.library.nyu.edu/fales/mss_213/all/",
        "rights_class": "D",
    },
    {
        "id": "nyu-fales-mss305",
        "collection": "NIGHTCLUBBING Archive by Pat Ivers and Emily Armstrong",
        "call_number": "MSS.305",
        "url": "https://findingaids.library.nyu.edu/fales/mss_305/all/",
        "rights_class": "D",
    },
]
MATCH_RE = re.compile(r"\bC\.?B\.?G\.?B\.?'?s?\b", re.IGNORECASE)
MEDIA_ID_RE = re.compile(r"\b(?:ID:\s*)?(\d{3}\.\d{4})\b")
DATE_RE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"\d{1,2}(?:st|nd|rd|th)?(?:,)?\s+\d{4}\b|\b(?:19|20)\d{2}\b",
    re.IGNORECASE,
)
BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "dt", "dd", "td", "th", "section", "article"}
SKIP_TAGS = {"script", "style", "noscript", "svg"}


class BlockParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, list[str]]] = []
        self.skip_depth = 0
        self.blocks: list[dict] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in BLOCK_TAGS:
            self.stack.append((tag, []))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth or tag not in BLOCK_TAGS:
            return
        for index in range(len(self.stack) - 1, -1, -1):
            stack_tag, parts = self.stack[index]
            if stack_tag != tag:
                continue
            self.stack.pop(index)
            text = re.sub(r"\s+", " ", "".join(parts)).strip()
            if text:
                self.blocks.append({"tag": tag, "text": text})
            break

    def handle_data(self, data: str) -> None:
        if self.skip_depth or not data:
            return
        for _, parts in self.stack:
            parts.append(data)


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def normalize_context(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def harvest(source: dict) -> dict:
    html = fetch_text(source["url"])
    parser = BlockParser()
    parser.feed(html)

    matches: list[dict] = []
    seen: set[str] = set()
    for block in parser.blocks:
        text = normalize_context(block["text"])
        if not MATCH_RE.search(text):
            continue
        # Limit giant section wrappers while keeping enough context to identify items.
        if len(text) > 5000:
            positions = [match.start() for match in MATCH_RE.finditer(text)]
            snippets = []
            for pos in positions:
                snippets.append(text[max(0, pos - 900) : min(len(text), pos + 1800)])
        else:
            snippets = [text]

        for snippet in snippets:
            snippet = normalize_context(snippet)
            fingerprint = hashlib.sha256(snippet.encode("utf-8")).hexdigest()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            media_ids = sorted(set(MEDIA_ID_RE.findall(snippet)))
            dates = sorted(set(DATE_RE.findall(snippet)))
            matches.append(
                {
                    "fingerprint": fingerprint,
                    "html_block_tag": block["tag"],
                    "media_ids": media_ids,
                    "date_mentions": dates,
                    "context": snippet,
                    "research_status": "unverified_finding_aid_match",
                }
            )

    return {
        **source,
        "html_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
        "matching_blocks": len(matches),
        "matches": matches,
        "rights_note": (
            "This output contains public catalog/finding-aid metadata only. "
            "Underlying archival media remains reference-only unless separate rights are cleared."
        ),
    }


def main() -> int:
    destination = pathlib.Path(
        sys.argv[1] if len(sys.argv) > 1 else "nyu-fales-cbgb-metadata.json"
    )
    records = []
    for source in SOURCES:
        print(f"Harvesting {source['call_number']} {source['collection']}...")
        try:
            records.append({"status": "ok", "data": harvest(source)})
        except Exception as exc:
            records.append(
                {
                    "status": "error",
                    "source": source,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    output = {
        "collector": "Open Concert Reality Evidence POC",
        "version": "0.3",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "subject": "CBGB & OMFUG / 313-315 Bowery",
        "policy": (
            "Catalog metadata discovery only. Do not treat finding-aid text as permission to copy, "
            "train on, redistribute, or publicly perform underlying archival media."
        ),
        "collections": records,
    }
    destination.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved NYU CBGB metadata harvest to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
