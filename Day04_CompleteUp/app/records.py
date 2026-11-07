"""Day 2/3/4: Load and query recipe records."""
from pathlib import Path
import json
from data.sample_records import SAMPLE_RECORDS

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "records.json"

def load_records():
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Warning: could not read records.json: {exc}")
    return [dict(record) for record in SAMPLE_RECORDS]

def search(keyword):
    keyword = keyword.lower().strip()
    if not keyword:
        return []
    results = []
    for record in load_records():
        searchable = " ".join([
            str(record.get("dish_name", "")),
            str(record.get("region_or_type", "")),
            " ".join(record.get("ingredients", []) or []),
        ]).lower()
        if keyword in searchable:
            results.append(record)
    return results

def count_by(field="region_or_type"):
    counts = {}
    for record in load_records():
        value = record.get(field) or "Unknown"
        counts[value] = counts.get(value, 0) + 1
    return counts

def get_by_id(recipe_id):
    for record in load_records():
        if str(record.get("id")) == str(recipe_id):
            return record
    return None
