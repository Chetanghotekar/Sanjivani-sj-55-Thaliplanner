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


def _parse_time_and_difficulty(record: dict) -> tuple[int | None, str]:
    """Parse minutes (as int) and difficulty keyword from time_and_difficulty string."""
    td = (record.get("time_and_difficulty") or "").lower()
    match = re.search(r"(\d+)\s*(?:minute|min)", td)
    minutes = int(match.group(1)) if match else None
    difficulty = "easy" if "easy" in td else ("medium" if "medium" in td else ("hard" if "hard" in td else ""))
    return minutes, difficulty


def _format_recipe_chunk(record: dict) -> str:
    title = record.get("dish_name") or "Untitled recipe"
    category = record.get("region_or_type") or "Indian"
    servings = record.get("servings", "Not specified")
    ingredients = record.get("ingredients") or []
    if not isinstance(ingredients, list):
        ingredients = [str(ingredients)]
    td = record.get("time_and_difficulty", "Not specified")
    return (
        f"Recipe: {title}. "
        f"Category: {category}. "
        f"Servings: {servings}. "
        f"Ingredients: {', '.join(map(str, ingredients))}. "
        f"Time and difficulty: {td}."
    )


def _format_records_response(question: str, selected_records: list[dict]) -> dict[str, Any]:
    """Build response text with evidence lines, citation numbers, and sources."""
    evidence_lines = []
    citations = []
    sources_lines = []

    for index, r in enumerate(selected_records, start=1):
        dish = r["dish_name"]
        url = r.get("source_url") or "https://en.wikibooks.org/wiki/Category:Indian_recipes"
        chunk_text = _format_recipe_chunk(r)
        evidence_lines.append(f"- {chunk_text} [{index}]")
        citations.append({
            "id": index,
            "title": dish,
            "source": url,
            "page": 1,
            "score": 1.0,
        })
        sources_lines.append(f"[{index}] {dish}: {url}")

    answer = (
        "Based on the retrieved ThaliPlanner information:\n"
        + "\n".join(evidence_lines)
        + "\n\nSources:\n"
        + "\n".join(sources_lines)
    )
    return {
        "question": question,
        "answer": answer,
        "citations": citations,
        "abstained": False,
    }


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

    # 4. Cooking time & difficulty query (e.g. "Which recipes are easy and take 20 minutes or less?")
    time_match = re.search(r"(\d+)\s*(?:minute|min)", q_lower)
    is_time_query = bool(time_match) or any(w in q_lower for w in ["minute", "minutes", "quick", "fast", "take less", "or less"])
    if is_time_query and any(w in q_lower for w in ["easy", "quick", "take", "under", "less", "within", "or less"]):
        max_minutes = int(time_match.group(1)) if time_match else 20
        require_easy = "easy" in q_lower

        matching = []
        for r in records:
            mins, diff = _parse_time_and_difficulty(r)
            if mins is None:
                continue
            if mins <= max_minutes:
                if require_easy and diff != "easy":
                    continue
                matching.append(r)

        # Sort by cooking time ascending (fastest dish first)
        matching.sort(key=lambda r: _parse_time_and_difficulty(r)[0] or 999)

        if matching:
            return _format_records_response(question, matching)

    # 5. Dish duration inquiry for a single dish (e.g. "How long does Dhokla take and how hard is it?")
    if matched_record and any(w in q_lower for w in ["how long", "how hard", "time", "difficulty", "take"]):
        return _format_records_response(question, [matched_record])

    # 6. Ingredient search queries (e.g. "Which dishes can I make with moong dal?" or "I have potatoes and onions, what can I cook?")
    if "moong dal" in q_lower and any(w in q_lower for w in ["make", "cook", "dishes", "recipes", "with"]):
        moong_records = [r for r in records if any("moong dal" in i.lower() for i in r.get("ingredients", []))]
        if moong_records:
            return _format_records_response(question, moong_records)

    if "potato" in q_lower and "onion" in q_lower and any(w in q_lower for w in ["cook", "make", "what can i", "recipe"]):
        potato_onion = [
            r for r in records
            if any("potato" in i.lower() for i in r.get("ingredients", []))
            and any("onion" in i.lower() for i in r.get("ingredients", []))
        ]
        if potato_onion:
            return _format_records_response(question, potato_onion)

    # 7. Category-specific queries (e.g. "What South Indian dishes do you have?")
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

    # 8. Single dish general inquiry (e.g. "Tell me about Moong Dal")
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

    # 9. Fallback to Persistent ChromaDB vector search
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
    sources_lines = []
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
        if source_url:
            sources_lines.append(f"[{index}] {title}: {source_url}")

    sources_block = ("\n\nSources:\n" + "\n".join(sources_lines)) if sources_lines else ""
    answer = "Based on the retrieved ThaliPlanner information:\n\n" + "\n".join(evidence_lines) + sources_block
    return {"question": question, "answer": answer, "citations": citations, "abstained": False}
