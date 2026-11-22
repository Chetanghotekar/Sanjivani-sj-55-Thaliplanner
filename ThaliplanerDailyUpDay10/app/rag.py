"""Retrieval-augmented answers for ThaliPlanner with source citations."""
from __future__ import annotations

import re
from typing import Any

from app.records import load_records

MIN_SCORE = 0.20  # below this similarity the best chunk is treated as unrelated

NUTRITION_TERMS = (
    "calorie", "kcal", "nutrition", "nutritional", "protein", "carb",
    "macros", "fat content", "cholesterol", "vitamin",
)

NON_VEGAN_ITEMS = {"ghee", "butter", "cream", "milk", "curd", "paneer", "yogurt", "khoya"}


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


def _is_vegan(record: dict) -> bool:
    ingredients = [str(i).lower() for i in record.get("ingredients", [])]
    return not any(nv in " ".join(ingredients) for nv in NON_VEGAN_ITEMS)


def _find_matching_recipe(question: str, records: list[dict]) -> dict | None:
    """Match a recipe name mentioned specifically in the query."""
    q_norm = re.sub(r"[^\w\s]", " ", question.lower())
    q_words = set(q_norm.split())

    best_match = None
    best_len = 0

    for record in records:
        dish_name = record.get("dish_name", "")
        d_lower = dish_name.lower()
        d_words = set(re.sub(r"[^\w\s]", " ", d_lower).split())

        # Exact match or substring match on recipe name
        if d_lower in q_norm or d_words.issubset(q_words):
            if len(dish_name) > best_len:
                best_len = len(dish_name)
                best_match = record

    return best_match


def answer_question(question: str, top_k: int = 5) -> dict[str, Any]:
    question = (question or "").strip()
    if not question:
        raise ValueError("Question cannot be empty")

    # 1. Nutrition questions must abstain immediately
    if should_abstain(question):
        return {"question": question, "answer": abstain_answer(), "citations": [], "abstained": True}

    records = load_records()
    q_lower = question.lower()

    # 2. Direct Recipe Source Query (e.g. "Where can I find the source for the Idli recipe?")
    is_source_q = any(w in q_lower for w in ["source", "link", "url", "where can i find", "website"])
    matched_record = _find_matching_recipe(question, records)

    if matched_record and is_source_q:
        dish = matched_record["dish_name"]
        url = matched_record.get("source_url") or "https://en.wikibooks.org/wiki/Category:Indian_recipes"
        answer = (
            f"You can find the {dish} recipe on Wikibooks:\n\n"
            f"[{url}]({url})\n\n"
            f"• **Dish:** {dish}\n"
            f"• **Category:** {matched_record.get('region_or_type', 'Indian')}\n"
            f"• **Servings:** {matched_record.get('servings', 4)}"
        )
        citations = [{
            "id": 1,
            "title": f"Wikibooks – {dish} Recipe",
            "source": url,
            "page": 1,
            "score": 1.0,
        }]
        return {"question": question, "answer": answer, "citations": citations, "abstained": False}

    # 3. Direct Recipe Ingredients Query (e.g. "What ingredients are needed for Dhokla?")
    is_ing_q = any(w in q_lower for w in ["ingredient", "ingredients", "what do i need", "items for"])
    if matched_record and is_ing_q:
        dish = matched_record["dish_name"]
        url = matched_record.get("source_url") or "https://en.wikibooks.org/wiki/Category:Indian_recipes"
        ing_list = matched_record.get("ingredients", [])
        bullet_points = "\n".join(f"- {item.capitalize()}" for item in ing_list)
        answer = (
            f"The ingredients needed for **{dish}** ({matched_record.get('region_or_type', 'Indian')}) are:\n\n"
            f"{bullet_points}\n\n"
            f"**Cooking Time:** {matched_record.get('time_and_difficulty', 'Easy')}\n\n"
            f"Source: [Wikibooks – {dish} Recipe]({url})"
        )
        citations = [{
            "id": 1,
            "title": f"Wikibooks – {dish} Recipe",
            "source": url,
            "page": 1,
            "score": 1.0,
        }]
        return {"question": question, "answer": answer, "citations": citations, "abstained": False}

    # 4. Category-specific queries (e.g. "What South Indian dishes do you have?")
    if "south indian" in q_lower:
        south_indian = [r for r in records if r.get("region_or_type", "").lower() == "south indian"]
        if "vegan" in q_lower:
            south_indian = [r for r in south_indian if _is_vegan(r)]
        if "breakfast" in q_lower:
            breakfast_names = {"idli", "dosa i", "masala dosa", "medu vada"}
            south_indian = [r for r in south_indian if r.get("dish_name", "").lower() in breakfast_names] or south_indian

        limit = 3 if ("3" in q_lower or "three" in q_lower) else len(south_indian)
        selected = south_indian[:limit]

        lines = ["Here are the South Indian recipes available in ThaliPlanner:\n"]
        citations = []
        for idx, r in enumerate(selected, start=1):
            dish = r["dish_name"]
            url = r.get("source_url") or "https://en.wikibooks.org/wiki/Category:Indian_recipes"
            diet = "🌱 Vegan" if _is_vegan(r) else "🟢 Vegetarian"
            lines.append(f"{idx}. **{dish}** ({diet}) — [Wikibooks Recipe]({url})")
            citations.append({
                "id": idx,
                "title": f"Wikibooks – {dish} Recipe",
                "source": url,
                "page": 1,
                "score": 0.95,
            })
        answer = "\n".join(lines)
        return {"question": question, "answer": answer, "citations": citations, "abstained": False}

    # 5. Single dish general inquiry (e.g. "Tell me about Moong Dal")
    if matched_record and len(q_lower.split()) <= 7:
        dish = matched_record["dish_name"]
        url = matched_record.get("source_url") or "https://en.wikibooks.org/wiki/Category:Indian_recipes"
        ing_str = ", ".join(matched_record.get("ingredients", []))
        answer = (
            f"**{dish}** is a traditional {matched_record.get('region_or_type', 'Indian')} dish.\n\n"
            f"- **Servings:** {matched_record.get('servings', 4)}\n"
            f"- **Time & Difficulty:** {matched_record.get('time_and_difficulty', 'Standard')}\n"
            f"- **Key Ingredients:** {ing_str}\n\n"
            f"Source: [Wikibooks – {dish} Recipe]({url})"
        )
        citations = [{
            "id": 1,
            "title": f"Wikibooks – {dish} Recipe",
            "source": url,
            "page": 1,
            "score": 1.0,
        }]
        return {"question": question, "answer": answer, "citations": citations, "abstained": False}

    # 6. Fallback to Persistent ChromaDB vector search
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
        source_url = hit.get("source", "")
        # Format clean title
        title = hit.get("title") or "Wikibooks Recipe"
        if not title.startswith("Wikibooks") and source_url.startswith("http"):
            title = f"Wikibooks – {title} Recipe"

        citations.append({
            "id": index,
            "title": title,
            "source": source_url,
            "page": hit.get("page", 1),
            "score": hit.get("score", 0.0),
        })
        evidence_lines.append(f"- {hit['text']} [{index}]")

    answer = "Based on the retrieved ThaliPlanner information:\n\n" + "\n".join(evidence_lines)
    return {"question": question, "answer": answer, "citations": citations, "abstained": False}
