"""S1: Embedding-based semantic search and 10-question evaluation."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import numpy as np

# Prefer offline cached weights to prevent slow 30-second HuggingFace network retry timeouts
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from app.chunking import ROOT, chunk_documents

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
QUESTIONS_FILE = ROOT / "eval" / "questions.md"
RESULTS_FILE = ROOT / "eval" / "search_results.md"
TOP_K = 5

_model = None


def get_model():
    """Load the embedding model once; first run may download it."""
    global _model
    if _model is None:
        try:
            # Imported here so the API can start (and /chat can work) even if
            # this heavy package is not installed yet.
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(MODEL_NAME)
        except Exception as exc:
            raise RuntimeError(
                "Could not load the sentence-transformer model. Check internet "
                "connection on the first run and install sentence-transformers."
            ) from exc
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.empty((0, 0), dtype=np.float32)
    vectors = get_model().encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype=np.float32)


def semantic_search(query: str, chunks: list[dict[str, Any]] | None = None,
                    top_k: int = TOP_K) -> list[dict[str, Any]]:
    """Return the most semantically similar chunks using cosine similarity."""
    query = (query or "").strip()
    if not query:
        return []
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    chunks = chunks if chunks is not None else chunk_documents()
    if not chunks:
        return []

    documents = [item["text"] for item in chunks]
    vectors = embed_texts(documents)
    query_vector = embed_texts([query])[0]

    # Embeddings are normalized, so dot product equals cosine similarity.
    scores = np.dot(vectors, query_vector)
    ranked_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for index in ranked_indices:
        item = chunks[int(index)]
        results.append({
            "text": item["text"],
            "score": round(float(scores[index]), 4),
            **item["metadata"],
        })
    return results


def load_evaluation_questions() -> list[str]:
    """Read numbered questions from eval/questions.md, preserving their wording."""
    if not QUESTIONS_FILE.exists():
        raise FileNotFoundError(f"Missing evaluation questions file: {QUESTIONS_FILE}")

    questions = []
    for line in QUESTIONS_FILE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\|\s*(\d+)\s*\|\s*(.*?)\s*\|", line)
        if match:
            question = re.sub(r"\*\*", "", match.group(2)).strip()
            if question and question.lower() != "question a user would ask":
                questions.append(question)
    if not questions:
        raise ValueError("No numbered questions found in eval/questions.md")
    return questions


def run_evaluation(top_k: int = TOP_K) -> Path:
    """Search all 10 evaluation questions and write actual retrieved hits."""
    questions = load_evaluation_questions()
    chunks = chunk_documents()
    if not chunks:
        raise RuntimeError("No documents were chunked. Check data/records.json and docs/.")

    # Embed the corpus once; semantic_search remains available for one-off queries.
    corpus_vectors = embed_texts([item["text"] for item in chunks])
    lines = [
        "# ThaliPlanner Semantic Search Evaluation",
        "",
        f"- Embedding model: `{MODEL_NAME}`",
        f"- Total chunks indexed for S1 evaluation: **{len(chunks)}**",
        f"- Questions evaluated: **{len(questions)}**",
        f"- Top K: **{top_k}**",
        "",
        "> Scores are cosine similarity between normalized sentence embeddings. "
        "Review retrieved text and source links; a high score is not a guarantee of correctness.",
        "",
    ]

    for number, question in enumerate(questions, start=1):
        query_vector = embed_texts([question])[0]
        scores = np.dot(corpus_vectors, query_vector)
        indices = np.argsort(scores)[::-1][:top_k]
        lines.extend([f"## {number}. {question}", ""])
        for rank, index in enumerate(indices, start=1):
            item = chunks[int(index)]
            meta = item["metadata"]
            lines.append(
                f"{rank}. **Score:** {float(scores[index]):.4f}  "
                f"**Title:** {meta.get('title', '')}  "
                f"**Page:** {meta.get('page', 1)}  "
                f"**Source:** `{meta.get('source', '')}`"
            )
            lines.append(f"   - {item['text']}")
        lines.append("")

    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text("\n".join(lines), encoding="utf-8")
    return RESULTS_FILE


if __name__ == "__main__":
    report = run_evaluation()
    print(f"Evaluation complete: {report}")
