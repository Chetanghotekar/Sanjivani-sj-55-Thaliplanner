"""S2: Persistent ChromaDB index for every ThaliPlanner chunk."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import chromadb

from app.chunking import ROOT, chunk_documents
from app.embed import embed_texts, MODEL_NAME

CHROMA_DIR = ROOT / "chroma_db"
COLLECTION_NAME = "thaliplanner_chunks"


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
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "description": "ThaliPlanner document chunks",
            "embedding_model": MODEL_NAME,
            "hnsw:space": "cosine",
        },
        # We supply our own sentence-transformer embeddings to Chroma.
    )


def build_index(rebuild: bool = True) -> int:
    """Embed all chunks and persist them in ChromaDB.

    rebuild=True clears the old collection first, preventing stale/duplicate chunks.
    """
    chunks = chunk_documents()
    if not chunks:
        raise RuntimeError("No chunks found. Check data/records.json and project documents.")

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    if rebuild:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "description": "ThaliPlanner document chunks",
            "embedding_model": MODEL_NAME,
            "hnsw:space": "cosine",
        },
    )

    texts = [item["text"] for item in chunks]
    embeddings = embed_texts(texts).tolist()
    ids = [_stable_id(item) for item in chunks]
    metadatas = [item["metadata"] for item in chunks]

    # Chroma has a per-request payload limit in some versions; add in batches.
    batch_size = 100
    for start in range(0, len(chunks), batch_size):
        end = start + batch_size
        collection.add(
            ids=ids[start:end],
            documents=texts[start:end],
            metadatas=metadatas[start:end],
            embeddings=embeddings[start:end],
        )

    return collection.count()


def search_chunks(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    query = (query or "").strip()
    if not query:
        return []
    if top_k < 1 or top_k > 50:
        raise ValueError("top_k must be between 1 and 50")

    collection = get_collection()
    if collection.count() == 0:
        build_index(rebuild=False)
        collection = get_collection()

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
