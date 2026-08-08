#!/usr/bin/env python3
"""Download only explicitly open-licensed CBGB images from Wikimedia Commons.

The collector intentionally ignores reference-only sources such as NYPL, Cornell,
press sites and social media. It records creator/license/source metadata beside
every downloaded file so reconstruction inputs stay auditable.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "OpenConcertRealityEvidencePOC/0.1 (https://github.com/DevOpsLabCode/demand-gig-engine)"
CATEGORIES = ["Category:CBGB 2009 (interior)", "Category:CBGB"]
ALLOWED_LICENSE_MARKERS = (
    "cc by 2.0",
    "cc by 2.5",
    "cc by 3.0",
    "cc by 4.0",
    "cc by-sa 2.0",
    "cc by-sa 2.5",
    "cc by-sa 3.0",
    "cc by-sa 4.0",
    "public domain",
    "cc0",
)


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
        titles.extend(item["title"] for item in data["query"]["categorymembers"])
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            return titles


def clean_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", value).strip()


def image_info(title: str) -> dict | None:
    data = api_get(
        {
            "action": "query",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|mime|size",
        }
    )
    pages = data.get("query", {}).get("pages", [])
    if not pages or not pages[0].get("imageinfo"):
        return None
    info = pages[0]["imageinfo"][0]
    metadata = info.get("extmetadata", {})
    return {
        "title": title,
        "url": info.get("url", ""),
        "description_url": info.get("descriptionurl", ""),
        "mime": info.get("mime", ""),
        "width": info.get("width"),
        "height": info.get("height"),
        "license_short": clean_html(metadata.get("LicenseShortName", {}).get("value", "")),
        "license_url": clean_html(metadata.get("LicenseUrl", {}).get("value", "")),
        "artist": clean_html(metadata.get("Artist", {}).get("value", "")),
        "credit": clean_html(metadata.get("Credit", {}).get("value", "")),
        "date_time_original": clean_html(metadata.get("DateTimeOriginal", {}).get("value", "")),
        "usage_terms": clean_html(metadata.get("UsageTerms", {}).get("value", "")),
    }


def license_allowed(info: dict) -> bool:
    text = " ".join(
        [info.get("license_short", ""), info.get("usage_terms", ""), info.get("license_url", "")]
    ).lower()
    return any(marker in text for marker in ALLOWED_LICENSE_MARKERS)


def safe_name(title: str) -> str:
    name = title.removeprefix("File:")
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")


def download(url: str, destination: pathlib.Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
        output.write(response.read())


def main() -> int:
    out_dir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "open-assets")
    out_dir.mkdir(parents=True, exist_ok=True)

    all_titles: list[str] = []
    for category in CATEGORIES:
        all_titles.extend(category_files(category))

    records: list[dict] = []
    seen: set[str] = set()
    for title in sorted(set(all_titles)):
        info = image_info(title)
        if not info or not info.get("url") or not license_allowed(info):
            continue
        filename = safe_name(title)
        if filename in seen:
            continue
        seen.add(filename)
        destination = out_dir / filename
        print(f"Downloading {title} -> {destination}")
        download(info["url"], destination)
        info["local_file"] = filename
        records.append(info)

    manifest = {
        "collector": "Open Concert Reality Evidence POC",
        "source": "Wikimedia Commons API",
        "categories": CATEGORIES,
        "downloaded_count": len(records),
        "note": "Verify attribution and share-alike obligations again before any public/commercial release.",
        "assets": records,
    }
    (out_dir / "attribution.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Saved {len(records)} open-licensed assets and attribution metadata in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
