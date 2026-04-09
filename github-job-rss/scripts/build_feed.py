import json
import os
import re
import sys
import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime, format_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import feedparser
import requests

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "sources.json"
OUTPUT_DIR = ROOT / "docs"
OUTPUT_FILE = OUTPUT_DIR / "feed.xml"
NOJEKYLL = OUTPUT_DIR / ".nojekyll"

DEFAULT_CHANNEL = {
    "title": "Game, Animation, and Art Jobs",
    "link": "https://example.com/",
    "description": "Aggregated jobs feed for Discord / MEE6.",
    "language": "en-us",
}


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "job"


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_datetime(entry: Any) -> datetime:
    candidates = [
        getattr(entry, "published_parsed", None),
        getattr(entry, "updated_parsed", None),
    ]
    for candidate in candidates:
        if candidate:
            return datetime(*candidate[:6], tzinfo=timezone.utc)

    text_candidates = [
        getattr(entry, "published", None),
        getattr(entry, "updated", None),
        entry.get("pubDate"),
    ]
    for text in text_candidates:
        if text:
            try:
                dt = parsedate_to_datetime(text)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass

    return datetime.now(timezone.utc)


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def matches_keywords(title: str, summary: str, include: list[str], exclude: list[str]) -> bool:
    text = f"{title} {summary}".lower()
    if include and not any(k.lower() in text for k in include):
        return False
    if exclude and any(k.lower() in text for k in exclude):
        return False
    return True


def stable_guid(link: str, title: str, source_name: str) -> str:
    raw = f"{source_name}|{link}|{title}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def fetch_feed(url: str) -> Any:
    headers = {
        "User-Agent": "job-feed-bot/1.0 (+https://github.com/)"
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return feedparser.parse(response.content)


def aggregate_entries(config: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()

    include = config.get("filters", {}).get("include_keywords", [])
    exclude = config.get("filters", {}).get("exclude_keywords", [])
    max_items = int(config.get("max_items", 100))

    for source in config.get("sources", []):
        if not source.get("enabled", True):
            continue

        name = source["name"]
        feed_url = source["feed_url"]

        try:
            parsed = fetch_feed(feed_url)
        except Exception as exc:
            print(f"[WARN] Failed to load {name}: {exc}", file=sys.stderr)
            continue

        for entry in parsed.entries:
            title = clean_text(entry.get("title"))
            link = clean_text(entry.get("link"))
            summary = clean_text(entry.get("summary") or entry.get("description"))
            if not title or not link:
                continue

            if not matches_keywords(title, summary, include, exclude):
                continue

            guid = stable_guid(link, title, name)
            if guid in seen:
                continue
            seen.add(guid)

            dt = parse_datetime(entry)
            entries.append(
                {
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "source": name,
                    "published": dt,
                    "guid": guid,
                    "hostname": urlparse(link).netloc,
                }
            )

    entries.sort(key=lambda x: x["published"], reverse=True)
    return entries[:max_items]


def build_rss(config: dict[str, Any], entries: list[dict[str, Any]]) -> ET.ElementTree:
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    channel_meta = DEFAULT_CHANNEL | config.get("channel", {})
    for key in ["title", "link", "description", "language"]:
        el = ET.SubElement(channel, key)
        el.text = str(channel_meta[key])

    last_build = ET.SubElement(channel, "lastBuildDate")
    last_build.text = format_datetime(datetime.now(timezone.utc))

    generator = ET.SubElement(channel, "generator")
    generator.text = "GitHub Actions + Python feed merger"

    for item in entries:
        item_el = ET.SubElement(channel, "item")

        title_el = ET.SubElement(item_el, "title")
        title_el.text = f"[{item['source']}] {item['title']}"

        link_el = ET.SubElement(item_el, "link")
        link_el.text = item["link"]

        guid_el = ET.SubElement(item_el, "guid", isPermaLink="false")
        guid_el.text = item["guid"]

        pub_el = ET.SubElement(item_el, "pubDate")
        pub_el.text = format_datetime(item["published"])

        category_el = ET.SubElement(item_el, "category")
        category_el.text = item["source"]

        desc_el = ET.SubElement(item_el, "description")
        body = item["summary"] or f"Source: {item['source']} ({item['hostname']})"
        desc_el.text = body

    return ET.ElementTree(rss)


def write_output(tree: ET.ElementTree) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tree.write(OUTPUT_FILE, encoding="utf-8", xml_declaration=True)
    NOJEKYLL.write_text("", encoding="utf-8")


if __name__ == "__main__":
    config = load_config()
    entries = aggregate_entries(config)
    rss_tree = build_rss(config, entries)
    write_output(rss_tree)
    print(f"Wrote {len(entries)} jobs to {OUTPUT_FILE}")
