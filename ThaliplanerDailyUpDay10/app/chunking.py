"""S1: Split ThaliPlanner documents into chunks with source/page/title metadata."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "records.json"

# Character-based chunking is predictable and does not require another package.
CHUNK_SIZE = 900
CHUNK_OVERLAP = 120
SUPPORTED_EXTENSIONS = {".md", ".txt", ".html", ".htm", ".json"}


def _clean_text(value: str) -> str:
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"[#*_>`|]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def split_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks, preferring word boundaries."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start + chunk_size // 2:
                end = boundary

        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)

        if end >= len(text):
            break
        next_start = max(end - overlap, start + 1)
        start = next_start

    return chunks


def _metadata(source: str, page: int, title: str, chunk_index: int) -> dict[str, Any]:
    return {
        "source": str(source),
        "page": int(page),
        "title": str(title or Path(source).stem),
        "chunk_index": int(chunk_index),
    }


def _chunks_for_text(text: str, source: str, title: str,
                     page: int = 1, chunk_size: int = CHUNK_SIZE,
                     overlap: int = CHUNK_OVERLAP) -> list[dict[str, Any]]:
    pieces = split_text(_clean_text(text), chunk_size=chunk_size, overlap=overlap)
    output = []
    for index, piece in enumerate(pieces):
        output.append({
            "text": piece,
            "metadata": _metadata(source, page, title, index),
        })
    return output


def _record_chunks(chunk_size: int = CHUNK_SIZE,
                   overlap: int = CHUNK_OVERLAP) -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        return []

    try:
        records = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read {DATA_FILE}: {exc}") from exc

    if not isinstance(records, list):
        raise ValueError("data/records.json must contain a JSON list")

    output = []
    for record in records:
        if not isinstance(record, dict):
            continue
        title = str(record.get("dish_name") or "Untitled recipe")
        ingredients = record.get("ingredients") or []
        if not isinstance(ingredients, list):
            ingredients = [str(ingredients)]

        text = (
            f"Recipe: {title}. "
            f"Category: {record.get('region_or_type', 'Unknown')}. "
            f"Servings: {record.get('servings', 'Not specified')}. "
            f"Ingredients: {', '.join(map(str, ingredients))}. "
            f"Time and difficulty: {record.get('time_and_difficulty', 'Not specified')}."
        )
        source = str(record.get("source_url") or "data/records.json")
        output.extend(_chunks_for_text(text, source, title, page=1,
                                       chunk_size=chunk_size, overlap=overlap))
    return output


def _read_document(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    raw = path.read_text(encoding="utf-8", errors="ignore")

    if suffix in {".html", ".htm"}:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(raw, "html.parser")
            title = soup.title.get_text(" ", strip=True) if soup.title else path.stem
            main = soup.select_one("#mw-content-text") or soup.body or soup
            return main.get_text(" ", strip=True), title
        except ImportError:
            return _clean_text(raw), path.stem

    title = path.stem
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            break
    if suffix == ".json":
        try:
            parsed = json.loads(raw)
            raw = json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
    return raw, title


def chunk_documents(chunk_size: int = CHUNK_SIZE,
                    overlap: int = CHUNK_OVERLAP) -> list[dict[str, Any]]:
    """Chunk records.json plus project docs and the raw recipe HTML.

    Each result has `text` and metadata containing `source`, `page`, `title`.
    Prompts, README.md, evaluation outputs and the Chroma database are
    intentionally excluded: they are not recipe knowledge, and README.md is
    rewritten by eval/run_eval.py, which would make evaluations unrepeatable.
    """
    chunks = _record_chunks(chunk_size=chunk_size, overlap=overlap)

    candidate_dirs = [ROOT / "docs", ROOT / "data" / "raw"]
    candidate_files = []

    for folder in candidate_dirs:
        if folder.exists():
            candidate_files.extend(
                path for path in folder.rglob("*")
                if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
            )

    seen = set()
    for path in sorted(candidate_files):
        if not path.exists() or not path.is_file():
            continue
        try:
            source = path.relative_to(ROOT).as_posix()
        except ValueError:
            source = path.name
        if source in seen:
            continue
        seen.add(source)

        # The structured recipe JSON is already converted into one chunk per recipe.
        if path.resolve() == DATA_FILE.resolve():
            continue

        text, title = _read_document(path)
        chunks.extend(_chunks_for_text(text, source, title, page=1,
                                       chunk_size=chunk_size, overlap=overlap))

    return chunks


if __name__ == "__main__":
    result = chunk_documents()
    print(f"Created {len(result)} chunks.")
    for item in result[:3]:
        print(item["metadata"], item["text"][:120])
