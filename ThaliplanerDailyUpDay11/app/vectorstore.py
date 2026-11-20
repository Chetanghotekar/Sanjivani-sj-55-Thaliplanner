"""S2: Persistent ChromaDB index for every ThaliPlanner chunk."""
from __future__ import annotations

import hashlib
from typing import Any

from app.chunking import ROOT, chunk_documents
from app.embed import embed_texts, MODEL_NAME

CHROMA_DIR = ROOT / "chroma_db"
COLLECTION_NAME = "thaliplanner_chunks"

# True once this process has confirmed the saved index matches the current documents.
_index_checked = False


def _client():
    # Imported here so the rest of the app still starts if chromadb is missing.
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def _collection_metadata() -> dict[str, str]:
    return {
        "description": "ThaliPlanner document chunks",
        "embedding_model": MODEL_NAME,
        "hnsw:space": "cosine",
    }


def _stable_id(item: dict[str, Any]) -> str:
    meta = item["metadata"]
    raw = "|".join([
        str(meta.get("source", "")),
        str(meta.get("page", 1)),
        str(meta.get("title", "")),
        str(meta.get("chunk_index", 0)),
        item["text"],
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_collection():
    # We supply our own sentence-transformer embeddings to Chroma.
    return _client().get_or_create_collection(
        name=COLLECTION_NAME, metadata=_collection_metadata()
    )


def build_index(rebuild: bool = True) -> int:
    """Embed all chunks and persist them in ChromaDB.

    rebuild=True clears the old collection first, preventing stale/duplicate chunks.
    """
    global _index_checked
    chunks = chunk_documents()
    if not chunks:
        raise RuntimeError("No chunks found. Check data/records.json and project documents.")

    client = _client()
    if rebuild:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:  # collection did not exist yet
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME, metadata=_collection_metadata()
    )

    # Identical chunks would get identical ids, which Chroma rejects inside one call.
    unique = {}
    for item in chunks:
        unique.setdefault(_stable_id(item), item)
    ids = list(unique)
    items = list(unique.values())
    texts = [item["text"] for item in items]
    metadatas = [item["metadata"] for item in items]
    embeddings = embed_texts(texts).tolist()

    # Chroma limits the size of one request, so add in batches. upsert (not add)
    # means running with rebuild=False can never fail on ids that already exist.
    batch_size = 100
    for start in range(0, len(ids), batch_size):
        end = start + batch_size
        collection.upsert(
            ids=ids[start:end],
            documents=texts[start:end],
            metadatas=metadatas[start:end],
            embeddings=embeddings[start:end],
        )

    _index_checked = True
    return collection.count()


def _ensure_fresh_index():
    """Build the index if it is empty or no longer matches the current documents."""
    global _index_checked
    collection = get_collection()
    if _index_checked and collection.count() > 0:
        return collection
    expected = len({_stable_id(item) for item in chunk_documents()})
    if collection.count() != expected:
        build_index(rebuild=True)
        collection = get_collection()
    _index_checked = True
    return collection


def search_chunks(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    query = (query or "").strip()
    if not query:
        return []
    if top_k < 1 or top_k > 50:
        raise ValueError("top_k must be between 1 and 50")

    collection = _ensure_fresh_index()
    if collection.count() == 0:
        return []

    query_embedding = embed_texts([query])[0].tolist()
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    for document, metadata, distance in zip(documents, metadatas, distances):
        metadata = metadata or {}
        # Chroma cosine distance is 1 - cosine similarity for cosine collections.
        similarity = 1.0 - float(distance)
        hits.append({
            "text": document,
            "score": round(similarity, 4),
            "source": metadata.get("source", ""),
            "page": metadata.get("page", 1),
            "title": metadata.get("title", ""),
        })
    return hits


if __name__ == "__main__":
    total = build_index(rebuild=True)
    print(f"ChromaDB index built successfully. Total chunks: {total}")
    print(f"Persistent database: {CHROMA_DIR}")
