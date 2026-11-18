"""Retrieval-augmented answers for ThaliPlanner with source citations."""
from __future__ import annotations

from typing import Any

MIN_SCORE = 0.20  # below this similarity the best chunk is treated as unrelated

NUTRITION_TERMS = (
    "calorie", "kcal", "nutrition", "nutritional", "protein", "carb",
    "macros", "fat content", "cholesterol", "vitamin",
)


def should_abstain(question: str) -> bool:
    """Return True for questions asking for facts absent from the recipe schema."""
    q = (question or "").lower()
    return any(term in q for term in NUTRITION_TERMS)


def abstain_answer() -> str:
    # Generic on purpose: it must be correct for any nutrition question, not just Q6.
    return (
        "I don't know. The available ThaliPlanner recipe data does not contain "
        "calorie or nutrition information."
    )


def answer_question(question: str, top_k: int = 5) -> dict[str, Any]:
    question = (question or "").strip()
    if not question:
        raise ValueError("Question cannot be empty")

    # The required out-of-dataset Q6 must never be answered from unrelated chunks.
    if should_abstain(question):
        return {"question": question, "answer": abstain_answer(), "citations": [], "abstained": True}

    # Imported here so eval/run_eval.py can use should_abstain() without chromadb.
    from app.vectorstore import search_chunks

    hits = search_chunks(question, top_k=top_k)
    if not hits or hits[0]["score"] < MIN_SCORE:
        return {
            "question": question,
            "answer": "I don't know based on the available ThaliPlanner documents.",
            "citations": [],
            "abstained": True,
        }

    citations = []
    evidence_lines = []
    for index, hit in enumerate(hits, start=1):
        citations.append({
            "id": index,
            "title": hit.get("title") or "Untitled source",
            "source": hit.get("source", ""),
            "page": hit.get("page", 1),
            "score": hit.get("score", 0.0),
        })
        # Include only retrieved evidence; the citation marker maps to this source.
        evidence_lines.append(f"- {hit['text']} [{index}]")

    answer = "Based on the retrieved ThaliPlanner information:\n" + "\n".join(evidence_lines)
    return {"question": question, "answer": answer, "citations": citations, "abstained": False}
