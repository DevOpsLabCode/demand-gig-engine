#!/usr/bin/env python3
"""Discover CBGB Wikimedia Commons assets and download only safe open-image candidates.

This collector has two goals that must stay separate:

1. maximize research recall by recording every file discovered in the configured
   Commons categories, including files we refuse to download; and
2. keep the actual reconstruction-input directory limited to files whose exact
   item metadata identifies an allow-listed open license and an image MIME type.

It does not touch NYPL, Cornell, NYU Fales, press, social media or other
reference-only sources. Those remain metadata links in the evidence graph.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = (
    "OpenConcertRealityEvidencePOC/0.2 "
    "(https://github.com/DevOpsLabCode/demand-gig-engine; research prototype)"
)
CATEGORIES = ["Category:CBGB 2009 (interior)", "Category:CBGB"]
ALLOWED_LICENSES = {
    "cc by 2.0",
    "cc by 2.5",
    "cc by 3.0",
    "cc by 4.0",
    "cc by-sa 2.0",
    "cc by-sa 2.5",
    "cc by-sa 3.0",
    "cc by-sa 4.0",
    "cc0",
    "cc0 1.0",
    "public domain",
    "pd-old",
    "pd-us",
}
ALLOWED_IMAGE_MIME_PREFIX = "image/"


def api_get(params: dict[str, str]) -> dict:
    query = urllib.parse.urlencode({"format": "json", "formatversion": "2", **params})
    request = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def category_files(category: str) -> list[str]:
    titles: list[str] = []
    cont: str | None = None
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmtype": "file",
            "cmlimit": "500",
        }
        if cont:
            params["cmcontinue"] = cont
        data = api_get(params)
        titles.extend(item["title"] for item in data.get("query", {}).get("categorymembers", []))
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            return titles


def clean_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", value).strip()


def meta_value(metadata: dict, key: str) -> str:
    return clean_html(metadata.get(key, {}).get("value", ""))


def image_info(title: str) -> dict | None:
    data = api_get(
        {
            "action": "query",
            "titles": title,
            "prop": "imageinfo|categories",
            "iiprop": "url|extmetadata|mime|size|sha1|timestamp",
            "cllimit": "500",
        }
    )
    pages = data.get("query", {}).get("pages", [])
    if not pages or not pages[0].get("imageinfo"):
        return None
    page = pages[0]
    info = page["imageinfo"][0]
    metadata = info.get("extmetadata", {})
    return {
        "title": title,
        "pageid": page.get("pageid"),
        "url": info.get("url", ""),
        "description_url": info.get("descriptionurl", ""),
        "mime": info.get("mime", ""),
        "width": info.get("width"),
        "height": info.get("height"),
        "bytes": info.get("size"),
        "commons_sha1": info.get("sha1", ""),
        "commons_timestamp": info.get("timestamp", ""),
        "license_short": meta_value(metadata, "LicenseShortName"),
        "license_url": meta_value(metadata, "LicenseUrl"),
        "artist": meta_value(metadata, "Artist"),
        "credit": meta_value(metadata, "Credit"),
        "date_time_original": meta_value(metadata, "DateTimeOriginal"),
        "usage_terms": meta_value(metadata, "UsageTerms"),
        "copyrighted": meta_value(metadata, "Copyrighted"),
        "restrictions": meta_value(metadata, "Restrictions"),
        "categories": [entry.get("title", "") for entry in page.get("categories", [])],
    }


def normalized_license(info: dict) -> str:
    return info.get("license_short", "").strip().lower()


def classify(info: dict) -> tuple[str, str]:
    if not info.get("url"):
        return "metadata_only", "no downloadable URL in Commons response"
    if not str(info.get("mime", "")).lower().startswith(ALLOWED_IMAGE_MIME_PREFIX):
        return "metadata_only", f"MIME type {info.get('mime')!r} is not an image reconstruction input"
    license_name = normalized_license(info)
    if license_name not in ALLOWED_LICENSES:
        return "metadata_only", f"license {info.get('license_short')!r} is not in the explicit POC allow-list"
    if info.get("restrictions"):
        return "metadata_only", f"Commons metadata contains restrictions: {info.get('restrictions')}"
    return "download_candidate", f"allow-listed item license: {info.get('license_short')}"


def safe_name(title: str) -> str:
    name = title.removeprefix("File:")
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")


def download(url: str, destination: pathlib.Path) -> str:
    digest = hashlib.sha256()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
            output.write(block)
    return digest.hexdigest()


def main() -> int:
    out_dir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "open-assets")
    out_dir.mkdir(parents=True, exist_ok=True)

    category_map: dict[str, set[str]] = {}
    for category in CATEGORIES:
        print(f"Discovering {category}...")
        category_map[category] = set(category_files(category))
        time.sleep(0.1)

    all_titles = sorted(set().union(*category_map.values())) if category_map else []
    discovered: list[dict] = []
    downloaded: list[dict] = []
    seen_filenames: set[str] = set()

    for title in all_titles:
        info = image_info(title)
        time.sleep(0.1)
        if info is None:
            discovered.append(
                {
                    "title": title,
                    "decision": "metadata_error",
                    "reason": "Commons API did not return imageinfo",
                    "discovered_in": [c for c, files in category_map.items() if title in files],
                }
            )
            continue

        info["discovered_in"] = [c for c, files in category_map.items() if title in files]
        decision, reason = classify(info)
        info["decision"] = decision
        info["reason"] = reason
        discovered.append(info.copy())

        if decision != "download_candidate":
            print(f"Metadata only: {title} ({reason})")
            continue

        filename = safe_name(title)
        if filename in seen_filenames:
            info["decision"] = "metadata_only"
            info["reason"] = "sanitized filename collision"
            continue
        seen_filenames.add(filename)

        destination = out_dir / filename
        print(f"Downloading {title} -> {destination}")
        sha256 = download(info["url"], destination)
        info["local_file"] = filename
        info["sha256"] = sha256
        info["decision"] = "downloaded"
        downloaded.append(info)

    research_manifest = {
        "collector": "Open Concert Reality Evidence POC",
        "version": "0.2",
        "source": "Wikimedia Commons API",
        "categories": CATEGORIES,
        "discovered_count": len(discovered),
        "records": discovered,
        "note": (
            "This manifest intentionally includes rejected/metadata-only files. "
            "Discovery does not grant reuse rights. Re-check item licenses before release."
        ),
    }
    attribution_manifest = {
        "collector": "Open Concert Reality Evidence POC",
        "version": "0.2",
        "source": "Wikimedia Commons API",
        "downloaded_count": len(downloaded),
        "assets": downloaded,
        "note": (
            "Only current allow-listed image candidates were downloaded. Verify attribution, "
            "license compatibility, share-alike and derivative obligations again before any public/commercial release."
        ),
    }

    (out_dir / "discovered.json").write_text(
        json.dumps(research_manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "attribution.json").write_text(
        json.dumps(attribution_manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"Discovered {len(discovered)} Commons files; downloaded {len(downloaded)} "
        f"allow-listed image candidates into {out_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
