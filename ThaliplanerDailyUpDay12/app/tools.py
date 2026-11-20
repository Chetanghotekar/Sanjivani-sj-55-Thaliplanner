"""Day 9: tools the agent can call.

build_grocery_list(selections)  - pure Python dictionaries and arithmetic, no LLM, no network.
search_recipes(query)           - RAG (vector) search that returns recipe IDs the agent can use.

Recipe records only list ingredient names, so quantities live in
data/ingredient_quantities.json (written for each recipe's own servings).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUANTITIES_FILE = ROOT / "data" / "ingredient_quantities.json"

# ---------------------------------------------------------------- conversion tables
# Volume units in millilitres.
VOLUME_ML = {"cup": 240.0, "tbsp": 15.0, "tsp": 5.0}
# Units that need no conversion table: (base unit, multiplier).
DIRECT_UNITS = {"g": ("g", 1.0), "kg": ("g", 1000.0), "ml": ("ml", 1.0), "l": ("ml", 1000.0)}

# Liquids stay in millilitres on the shopping list.
LIQUIDS = {"water", "milk", "oil", "cream", "lemon juice", "vinegar", "dosa batter"}

# Approximate grams in one cup (240 ml) of each solid ingredient.
GRAMS_PER_CUP = {
    "rice": 185, "idli rice": 190, "moong dal": 200, "toor dal": 200, "urad dal": 200,
    "whole urad dal": 200, "chana dal": 200, "chickpeas": 200, "gram flour": 90,
    "sugar": 200, "salt": 290, "turmeric": 130, "cumin": 100, "mustard seeds": 190,
    "fenugreek seeds": 200, "pepper": 110, "spices": 100, "sambar powder": 100,
    "chole masala": 100, "tamarind": 260, "green peas": 150, "butter": 227,
    "ghee": 220, "coconut": 80, "tea": 100, "yogurt": 245, "eno": 240,
}

# Approximate grams for one "piece" of a whole item (others stay as a piece count).
PIECE_GRAMS = {"potato": 150, "onion": 100, "tomato": 100, "mango": 300,
               "green chilli": 5, "red chilli": 2}

# Spelling variants, so "potatoes" and "potato" are added together.
ALIASES = {"potatoes": "potato", "tomatoes": "tomato", "onions": "onion",
           "chillies": "chilli", "green chillies": "green chilli",
           "red chillies": "red chilli", "mangoes": "mango"}


# ---------------------------------------------------------------- helpers
def normalize_item(name: str) -> str:
    key = " ".join(str(name).lower().split())
    return ALIASES.get(key, key)


def load_quantities(path: Path = QUANTITIES_FILE) -> dict[str, list]:
    """Return {recipe_id (str): [[item, qty, unit], ...]}. Missing file means no quantities."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    recipes = data.get("recipes") if isinstance(data, dict) else None
    return recipes if isinstance(recipes, dict) else {}


def convert_to_base(item: str, qty: float, unit: str) -> tuple[float, str, str | None]:
    """Convert one ingredient amount to grams or millilitres when the table allows.

    Returns (quantity, unit, warning). When no conversion is known the amount is
    kept in its own unit and a warning explains why.
    """
    unit = str(unit).lower().strip()
    if unit in DIRECT_UNITS:
        base, factor = DIRECT_UNITS[unit]
        return qty * factor, base, None
    if unit in VOLUME_ML:
        ml = qty * VOLUME_ML[unit]
        if item in LIQUIDS:
            return ml, "ml", None
        if item in GRAMS_PER_CUP:
            return ml / VOLUME_ML["cup"] * GRAMS_PER_CUP[item], "g", None
        return qty, unit, f"no gram/ml conversion for '{item}', kept in {unit}"
    if unit == "piece" and item in PIECE_GRAMS:
        return qty * PIECE_GRAMS[item], "g", None
    return qty, unit, None  # counts such as "piece" stay as counts


def _round(value: float) -> float:
    return round(value) if value >= 10 else round(value, 1)


def _display(qty: float, unit: str) -> str:
    if unit == "g" and qty >= 1000:
        return f"{qty / 1000:.2f}".rstrip("0").rstrip(".") + " kg"
    if unit == "ml" and qty >= 1000:
        return f"{qty / 1000:.2f}".rstrip("0").rstrip(".") + " l"
    text = f"{qty:g}"
    return f"{text} {unit}"


def _valid_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


# ---------------------------------------------------------------- tool 1
def build_grocery_list(selections: list[dict], records: list[dict] | None = None,
                       quantities: dict | None = None) -> dict[str, Any]:
    """Scale chosen recipes to target servings and merge them into one shopping list.

    selections: [{"recipe_id": 1, "servings": 8}, ...]  ("servings" is optional and
    defaults to the recipe's own servings).

    Returns {"items", "unquantified", "recipes", "missing_recipes", "warnings"}.
    Raises ValueError if the input itself is malformed.
    """
    if not isinstance(selections, list) or not selections:
        raise ValueError("selections must be a non-empty list of {recipe_id, servings}")
    if records is None:
        from app.records import load_records
        records = load_records()
    if quantities is None:
        quantities = load_quantities()
    by_id = {str(r.get("id")): r for r in records}

    totals: dict[tuple[str, str], dict] = {}      # (item, unit) -> running total
    unquantified: dict[str, dict] = {}            # item -> recipes that need it
    used, missing, warnings = [], [], []

    for entry in selections:
        if not isinstance(entry, dict) or "recipe_id" not in entry:
            raise ValueError("each selection needs a recipe_id")
        rid = str(entry["recipe_id"])
        record = by_id.get(rid)
        if record is None:
            missing.append(entry["recipe_id"])
            continue

        base = record.get("servings")
        target = entry.get("servings", base)
        if not _valid_number(target):
            raise ValueError(f"servings for recipe {rid} must be a positive number")
        if not _valid_number(base):
            warnings.append(f"{record.get('dish_name')}: recipe has no servings value, cannot scale")
            continue

        scale = target / base
        name = record.get("dish_name", f"Recipe {rid}")
        used.append({"id": record.get("id"), "name": name, "base_servings": base,
                     "target_servings": target, "scale": round(scale, 3)})

        known = set()
        for item, qty, unit in quantities.get(rid, []):
            item = normalize_item(item)
            known.add(item)
            amount, base_unit, warning = convert_to_base(item, qty * scale, unit)
            if warning:
                warnings.append(f"{name}: {warning}")
            slot = totals.setdefault((item, base_unit), {"quantity": 0.0, "from": []})
            slot["quantity"] += amount
            if name not in slot["from"]:
                slot["from"].append(name)

        # Ingredients the record lists but we have no amount for are never guessed.
        for raw in record.get("ingredients") or []:
            item = normalize_item(raw)
            if item not in known:
                slot = unquantified.setdefault(item, {"item": item, "from": []})
                if name not in slot["from"]:
                    slot["from"].append(name)

    items = []
    for (item, unit), slot in sorted(totals.items()):
        qty = _round(slot["quantity"])
        items.append({"item": item, "quantity": qty, "unit": unit,
                      "display": _display(qty, unit), "from": slot["from"]})
    return {
        "items": items,
        "unquantified": sorted(unquantified.values(), key=lambda x: x["item"]),
        "recipes": used,
        "missing_recipes": missing,
        "warnings": warnings,
    }


# ---------------------------------------------------------------- tool 2
def search_recipes(query: str, top_k: int = 5) -> dict[str, Any]:
    """RAG search that returns recipes (with IDs) matching the query.

    Uses the ChromaDB vector search and maps chunk titles back to recipe records.
    If the vector store is not available it falls back to the keyword search.
    """
    from app.records import load_records

    query = (query or "").strip()
    if not query:
        raise ValueError("query cannot be empty")
    top_k = max(1, min(int(top_k), 10))
    records = load_records()
    by_title = {str(r.get("dish_name", "")).lower(): r for r in records}
    quantified = set(load_quantities())

    found, method, note = [], "rag", None
    try:
        from app.vectorstore import search_chunks
        # Ask for extra chunks: some hits are docs/raw pages, not recipe records.
        for hit in search_chunks(query, top_k=min(top_k * 4, 50)):
            record = by_title.get(str(hit.get("title", "")).lower())
            if record and all(record["id"] != f["id"] for f in found):
                found.append({**record, "score": hit.get("score")})
            if len(found) >= top_k:
                break
    except Exception as exc:  # vector store missing, not built, or model unavailable
        note = f"vector search unavailable ({type(exc).__name__}); used keyword search"

    if not found:
        from app.smart_search import smart_search
        method = "keyword_fallback"
        found = smart_search(query, top_k)

    results = [{
        "id": r["id"], "dish_name": r.get("dish_name"), "type": r.get("region_or_type"),
        "servings": r.get("servings"), "time_and_difficulty": r.get("time_and_difficulty"),
        "ingredients": r.get("ingredients"), "score": r.get("score"),
        "has_quantities": str(r["id"]) in quantified,
    } for r in found]
    out = {"method": method, "results": results}
    if note:
        out["note"] = note
    return out
