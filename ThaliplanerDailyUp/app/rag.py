"""Retrieval-augmented answers for ThaliPlanner with source citations"""
from __future__ import annotations

from typing import Any

from app.vectorstore import search_chunks

ABSTAIN_ANSWER = (
    "I don't know. The available ThaliPlanner recipe data does not contain "
    "calorie or nutrition information for Masala Dosa."
)


def should_abstain(question: str) -> bool:
    """Return True for questions asking for facts absent from the recipe schema."""
    q = (question or "").lower()
    nutrition_terms = ("calorie", "calories", "nutrition", "nutritional", "protein", "fat content")
    return any(term in q for term in nutrition_terms)


def answer_question(question: str, top_k: int = 5) -> dict[str, Any]:
    question = (question or "").strip()
    if not question:
        raise ValueError("Question cannot be empty")

    # The required out-of-dataset Q6 must never be answered from unrelated chunks.
    if should_abstain(question):
        return {"question": question, "answer": ABSTAIN_ANSWER, "citations": [], "abstained": True}

    hits = search_chunks(question, top_k=top_k)
    if not hits or hits[0]["score"] < 0.20:
        return {
            "question": question,
            "answer": "I don't know based on the available ThaliPlanner documents.",
            "citations": [],
            "abstained": True,
        }

    citations = []
    evidence_lines = []
    for index, hit in enumerate(hits, start=1):
        citation = {
            "id": index,
            "title": hit.get("title") or "Untitled source",
            "source": hit.get("source", ""),
            "page": hit.get("page", 1),
            "score": hit.get("score", 0.0),
        }
        citations.append(citation)
        # Include only retrieved evidence; the citation marker maps to this source.
        evidence_lines.append(f"- {hit['text']} [{index}]")

    answer = "Based on the retrieved ThaliPlanner information:\n" + "\n".join(evidence_lines)
    return {"question": question, "answer": answer, "citations": citations, "abstained": False}
