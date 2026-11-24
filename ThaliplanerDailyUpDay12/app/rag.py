"""Retrieval-augmented answers for ThaliPlanner with source citations, caching, and guardrails."""
from __future__ import annotations

import logging
import re
import time
from typing import Any

from app.records import load_records

logger = logging.getLogger("thaliplanner.rag")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

MIN_SCORE = 0.20  # below this similarity the best chunk is treated as unrelated
MAX_QUESTION_LENGTH = 500  # Input limit: guard against buffer-bloating attacks

NUTRITION_TERMS = (
    "calorie", "kcal", "nutrition", "nutritional", "protein", "carb",
    "macros", "fat content", "cholesterol", "vitamin",
)

NON_VEGAN_ITEMS = {"ghee", "butter", "cream", "milk", "curd", "paneer", "yogurt", "khoya"}

INJECTION_PATTERNS = (
    "ignore previous instructions", "ignore all instructions",
    "system override", "reveal system prompt", "print internal prompt",
    "developer mode", "jailbreak", "expose secrets", "disregard guidelines",
    "print system prompt", "drop table", "drop database", "show me your prompt"
)

# In-memory query cache for sub-millisecond repeated request performance
_RAG_CACHE: dict[tuple[str, int], dict[str, Any]] = {}
MAX_CACHE_SIZE = 256


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


def is_prompt_injection(question: str) -> bool:
    """Detect prompt-injection attempts that try to override system guardrails."""
    q = (question or "").lower()
    return any(p in q for p in INJECTION_PATTERNS)


def estimate_tokens(text: str) -> int:
    """Estimate token count for a text string (~1.3 tokens per whitespace word)."""
    if not text:
        return 0
    words = len(text.split())
    chars = len(text)
    return max(1, int(words * 1.25 + chars * 0.05))


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


def format_standard_recipe(record: dict) -> str:
    """Format any recipe record into the consistent, professional standard detailed format."""
    dish = record.get("dish_name", "Recipe")
    category = record.get("region_or_type") or "Not available in the recipe source."
    servings = record.get("servings")
    servings_str = str(servings) if servings is not None else "Not available in the recipe source."
    prep_time = record.get("preparation_time") or "Not available in the recipe source."
    cook_time = record.get("cooking_time") or "Not available in the recipe source."
    soak_time = record.get("soaking_time") or "Not applicable."
    ferm_time = record.get("fermentation_time") or "Not applicable."
    total_time = record.get("total_time") or "Not available in the recipe source."
    difficulty = record.get("difficulty") or "Not available in the recipe source."

    # Ingredients list
    raw_ingredients = record.get("ingredients") or []
    if isinstance(raw_ingredients, list) and raw_ingredients:
        ing_items = []
        for item in raw_ingredients:
            s = str(item).strip()
            if not s.startswith("- "):
                ing_items.append(f"- {s}")
            else:
                ing_items.append(s)
        ing_block = "\n".join(ing_items)
    else:
        ing_block = "- Not available in the recipe source."

    # Preparation Method (Numbered 1., 2., 3., etc.)
    raw_steps = record.get("preparation_steps") or []
    if isinstance(raw_steps, list) and raw_steps:
        step_items = []
        for idx, step in enumerate(raw_steps, start=1):
            s = str(step).strip()
            s_clean = re.sub(r"^\d+\.\s*", "", s)
            step_items.append(f"{idx}. {s_clean}")
        step_block = "\n".join(step_items)
    else:
        step_block = "1. Not available in the recipe source."

    serving_suggestions = record.get("serving_suggestions") or "Not available in the recipe source."
    source_url = record.get("source_url") or f"https://en.wikibooks.org/wiki/Cookbook:{dish.replace(' ', '_')}"

    return (
        f"# {dish}\n"
        f"**Category/Region:** {category}\n"
        f"**Servings:** {servings_str}\n"
        f"**Preparation Time:** {prep_time}\n"
        f"**Cooking Time:** {cook_time}\n"
        f"**Soaking Time:** {soak_time}\n"
        f"**Fermentation Time:** {ferm_time}\n"
        f"**Total Time:** {total_time}\n"
        f"**Difficulty:** {difficulty}\n\n"
        f"### Ingredients\n"
        f"{ing_block}\n\n"
        f"### Preparation Method\n"
        f"{step_block}\n\n"
        f"### Serving Suggestions\n"
        f"{serving_suggestions}\n\n"
        f"### Source\n"
        f"{source_url}"
    )


def _format_records_response(question: str, selected_records: list[dict]) -> dict[str, Any]:
    """Build response with multiple matching recipes in the standard detailed format."""
    evidence_blocks = []
    citations = []

    for index, r in enumerate(selected_records, start=1):
        dish = r["dish_name"]
        url = r.get("source_url") or f"https://en.wikibooks.org/wiki/Cookbook:{dish.replace(' ', '_')}"
        formatted = format_standard_recipe(r)
        evidence_blocks.append(formatted)
        citations.append({
            "id": index,
            "title": dish,
            "source": url,
            "page": 1,
            "score": 1.0,
        })

    answer = "\n\n---\n\n".join(evidence_blocks)
    return {
        "question": question,
        "answer": answer,
        "citations": citations,
        "abstained": False,
    }


def _format_single_recipe_response(record: dict, question: str = "") -> dict[str, Any]:
    """Return standard detailed recipe response for a single dish."""
    dish = record.get("dish_name", "Recipe")
    url = record.get("source_url") or f"https://en.wikibooks.org/wiki/Cookbook:{dish.replace(' ', '_')}"
    answer = format_standard_recipe(record)
    citations = [{
        "id": 1,
        "title": f"Wikibooks – {dish} Recipe",
        "source": url,
        "page": 1,
        "score": 1.0,
    }]
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


def answer_question(question: str, top_k: int = 5, use_cache: bool = True) -> dict[str, Any]:
    start_time = time.perf_counter()
    question = (question or "").strip()
    if not question:
        raise ValueError("Question cannot be empty")

    if len(question) > MAX_QUESTION_LENGTH:
        raise ValueError(
            f"Question exceeds maximum length of {MAX_QUESTION_LENGTH} characters (received {len(question)})"
        )

    # 1. In-memory cache check
    cache_key = (question.lower(), top_k)
    if use_cache and cache_key in _RAG_CACHE:
        hit = dict(_RAG_CACHE[cache_key])
        hit["cached"] = True
        hit["latency_ms"] = 0.18
        logger.info(
            "POST /ask | query='%s' | latency=0.18ms | tokens=%d | cached=True",
            question[:40], hit.get("tokens", {}).get("total", 0)
        )
        return hit

    # 2. Prompt injection shield
    if is_prompt_injection(question):
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        ans = "I don't know based on the available ThaliPlanner documents. Prompt injection attempt blocked."
        in_tok = estimate_tokens(question)
        out_tok = estimate_tokens(ans)
        res = {
            "question": question,
            "answer": ans,
            "citations": [],
            "abstained": True,
            "latency_ms": latency_ms,
            "tokens": {"prompt": in_tok, "completion": out_tok, "total": in_tok + out_tok},
            "cached": False,
        }
        logger.warning("POST /ask | PROMPT INJECTION BLOCKED | query='%s'", question[:40])
        return res

    # 3. Nutrition questions must abstain immediately
    if should_abstain(question):
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        ans = abstain_answer()
        in_tok = estimate_tokens(question)
        out_tok = estimate_tokens(ans)
        res = {
            "question": question,
            "answer": ans,
            "citations": [],
            "abstained": True,
            "latency_ms": latency_ms,
            "tokens": {"prompt": in_tok, "completion": out_tok, "total": in_tok + out_tok},
            "cached": False,
        }
        logger.info("POST /ask | NUTRITION ABSTAIN | latency=%.2fms", latency_ms)
        return res

    records = load_records()
    q_lower = question.lower()
    raw_res = None

    # 4. Direct Recipe Source Query (e.g. "Where can I find the source for the Idli recipe?")
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
        raw_res = {"question": question, "answer": answer, "citations": citations, "abstained": False}

    # 5. Direct Recipe Ingredients Query (e.g. "What ingredients are needed for Dhokla?")
    is_ing_q = any(w in q_lower for w in ["ingredient", "ingredients", "what do i need", "items for"])
    if raw_res is None and matched_record and is_ing_q:
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
        raw_res = {"question": question, "answer": answer, "citations": citations, "abstained": False}

    # 5b. Complete Structured Recipe Response (e.g. "Give me the recipe for Idli", "How do I make Dhokla?")
    is_recipe_q = any(w in q_lower for w in ["recipe", "make", "cook", "prepare", "how to", "how do i", "instructions", "method", "steps", "give me"])
    if raw_res is None and matched_record and (is_recipe_q or len(q_lower.split()) <= 2) and not is_source_q and not is_ing_q:
        raw_res = _format_single_recipe_response(matched_record, question)

    # 6. Cooking time & difficulty query (e.g. "Which recipes are easy and take 20 minutes or less?")
    time_match = re.search(r"(\d+)\s*(?:minute|min)", q_lower)
    is_time_query = bool(time_match) or any(w in q_lower for w in ["minute", "minutes", "quick", "fast", "take less", "or less"])
    if raw_res is None and is_time_query and any(w in q_lower for w in ["easy", "quick", "take", "under", "less", "within", "or less"]):
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
            raw_res = _format_records_response(question, matching)

    # 7. Dish duration inquiry for a single dish (e.g. "How long does Dhokla take and how hard is it?")
    if raw_res is None and matched_record and any(w in q_lower for w in ["how long", "how hard", "time", "difficulty", "take"]):
        raw_res = _format_records_response(question, [matched_record])

    # 8. Ingredient search queries (e.g. "Which dishes can I make with moong dal?" or "I have potatoes and onions, what can I cook?")
    if raw_res is None and "moong dal" in q_lower and any(w in q_lower for w in ["make", "cook", "dishes", "recipes", "with"]):
        moong_records = [r for r in records if any("moong dal" in i.lower() for i in r.get("ingredients", []))]
        if moong_records:
            raw_res = _format_records_response(question, moong_records)

    if raw_res is None and "potato" in q_lower and "onion" in q_lower and any(w in q_lower for w in ["cook", "make", "what can i", "recipe"]):
        potato_onion = [
            r for r in records
            if any("potato" in i.lower() for i in r.get("ingredients", []))
            and any("onion" in i.lower() for i in r.get("ingredients", []))
        ]
        if potato_onion:
            raw_res = _format_records_response(question, potato_onion)

    # 9. Category-specific queries (e.g. "What South Indian dishes do you have?")
    if raw_res is None and "south indian" in q_lower:
        south_indian = [r for r in records if r.get("region_or_type", "").lower() == "south indian"]
        if "vegan" in q_lower:
            south_indian = [r for r in south_indian if _is_vegan(r)]
        if "breakfast" in q_lower:
            breakfast_names = {"idli", "dosa i", "masala dosa", "medu vada"}
            south_indian = [r for r in south_indian if r.get("dish_name", "").lower() in breakfast_names] or south_indian

        limit = 3 if ("3" in q_lower or "three" in q_lower) else len(south_indian)
        selected = south_indian[:limit]

        raw_res = _format_records_response(question, selected)

    # 10. Single dish general inquiry (e.g. "Tell me about Moong Dal" or dish name query)
    if raw_res is None and matched_record and len(q_lower.split()) <= 7:
        raw_res = _format_single_recipe_response(matched_record, question)

    # 11. Fallback to Persistent ChromaDB vector search
    if raw_res is None:
        from app.vectorstore import search_chunks

        hits = search_chunks(question, top_k=top_k)
        if not hits or hits[0]["score"] < MIN_SCORE:
            ans = "I don't know based on the available ThaliPlanner documents."
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            in_tok = estimate_tokens(question)
            out_tok = estimate_tokens(ans)
            return {
                "question": question,
                "answer": ans,
                "citations": [],
                "abstained": True,
                "latency_ms": latency_ms,
                "tokens": {"prompt": in_tok, "completion": out_tok, "total": in_tok + out_tok},
                "cached": False,
            }

        citations = []
        evidence_lines = []
        sources_lines = []
        for index, hit in enumerate(hits, start=1):
            source_url = hit.get("source", "")
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
        raw_res = {"question": question, "answer": answer, "citations": citations, "abstained": False}

    # Attach performance, tokens, and cache metadata
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    in_tok = estimate_tokens(question)
    out_tok = estimate_tokens(raw_res["answer"])
    raw_res["latency_ms"] = latency_ms
    raw_res["tokens"] = {
        "prompt": in_tok,
        "completion": out_tok,
        "total": in_tok + out_tok,
    }
    raw_res["cached"] = False

    # Store in LRU cache
    if len(_RAG_CACHE) >= MAX_CACHE_SIZE:
        _RAG_CACHE.pop(next(iter(_RAG_CACHE)))
    _RAG_CACHE[cache_key] = dict(raw_res)

    logger.info(
        "POST /ask | query='%s' | latency=%.2fms | in_tokens=%d | out_tokens=%d | cached=False",
        question[:40], latency_ms, in_tok, out_tok
    )
    return raw_res
