"""Day 3: Convert downloaded Wikibooks HTML into recipe JSON.

The parser extracts headings and ingredient-like list items. Wikibooks layouts
vary, so it is intentionally conservative: unavailable servings/ingredients
remain None/[] and are not fabricated. Curated Day 2 sample records are merged
to ensure the requested 20 full starter records remain available.
"""
from pathlib import Path
import json
import re
from bs4 import BeautifulSoup
from app.models import Record
from data.sample_records import SAMPLE_RECORDS

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
OUTPUT = ROOT / "data" / "records.json"

def clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()

def parse_page(path, first_id):
    parsed = []
    if not path.exists():
        return parsed
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    content = soup.select_one("#mw-content-text") or soup
    headings = content.find_all(["h2", "h3"])
    for heading in headings:
        name = clean_text(heading.get_text(" ", strip=True))
        name = re.sub(r"\[edit\]$", "", name).strip()
        if not name or name.lower() in {"contents", "references", "see also", "external links"}:
            continue
        ingredients = []
        node = heading.find_next_sibling()
        while node and node.name not in {"h2", "h3"}:
            if node.name in {"ul", "ol"}:
                for li in node.find_all("li", recursive=False):
                    item = clean_text(li.get_text(" ", strip=True))
                    if item and len(item) < 180:
                        ingredients.append(item)
            node = node.find_next_sibling()
        # Only retain a section when it appears recipe-like.
        if ingredients:
            parsed.append(Record(
                id=first_id + len(parsed),
                dish_name=name,
                region_or_type="Wikibooks",
                servings=None,
                ingredients=ingredients[:40],
                time_and_difficulty="",
                source_url="https://en.wikibooks.org/wiki/Cookbook"
            ).to_dict())
    return parsed

def ingest():
    extracted = []
    for html_file in sorted(RAW_DIR.glob("*.html")):
        extracted.extend(parse_page(html_file, 1000 + len(extracted)))

    # Keep Day 2's 20 curated complete starter records, then add non-duplicate
    # source-extracted records. The curated fields are explicitly provided data.
    records = [dict(item) for item in SAMPLE_RECORDS]
    existing = {item["dish_name"].strip().lower() for item in records}
    for item in extracted:
        key = item["dish_name"].strip().lower()
        if key and key not in existing:
            records.append(item)
            existing.add(key)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(records)} records to {OUTPUT}")
    print(f"Source-extracted additional records: {len(records) - len(SAMPLE_RECORDS)}")
    return records

if __name__ == "__main__":
    ingest()
