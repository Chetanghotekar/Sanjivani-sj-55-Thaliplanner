"""Day 11 Tests: 9 tests covering records, search, /health, /ask with fake LLM, and agent tool."""
from app import main
from app.records import load_records, get_by_id
from app.smart_search import smart_search
from app.tools import build_grocery_list, load_quantities, convert_to_base, normalize_item


# 1. Health check endpoint test
def test_health_endpoint():
    assert main.health() == {"status": "ok"}


# 2. Records loading test
def test_load_records_has_at_least_20():
    records = load_records()
    assert isinstance(records, list)
    assert len(records) >= 20
    assert any(r["dish_name"] == "Moong Dal" for r in records)


# 3. Get record by ID test
def test_get_by_id():
    rec = get_by_id(1)
    assert rec is not None
    assert rec["dish_name"] == "Moong Dal"
    assert get_by_id(99999) is None


# 4. Search function test
def test_smart_search_returns_relevant_records():
    results = smart_search("moong dal", limit=5)
    assert len(results) > 0
    assert results[0]["dish_name"] == "Moong Dal"


# 5. /ask question answering with fake LLM / abstain test
def test_ask_endpoint_abstain():
    res = main.ask(main.AskRequest(question="How many calories are in a Masala Dosa?"))
    assert res["abstained"] is True
    assert res["answer"].startswith("I don't know.")


# 6. /ask endpoint with fake LLM response
def test_ask_with_fake_llm(monkeypatch):
    class FakeRAGAnswer:
        @staticmethod
        def answer(question, top_k=5):
            return {
                "question": question,
                "answer": "Moong Dal is a nutritious lentil dish.",
                "citations": [{"source": "https://en.wikibooks.org/wiki/Cookbook:Moong_Dal", "chunk": "Moong Dal"}],
                "abstained": False,
            }
    monkeypatch.setattr(main, "answer_question", FakeRAGAnswer.answer)
    res = main.ask(main.AskRequest(question="Tell me about Moong Dal"))
    assert res["abstained"] is False
    assert "Moong Dal" in res["answer"]
    assert len(res["citations"]) == 1


# 7. Agent grocery list tool scaling & conversion test
def test_agent_tool_build_grocery_list_scaling():
    records = load_records()
    quantities = load_quantities()
    selections = [{"recipe_id": 1, "servings": 8}]
    result = build_grocery_list(selections, records, quantities)
    moong = next(i for i in result["items"] if i["item"] == "moong dal")
    assert moong["quantity"] == 400
    assert moong["unit"] == "g"
    assert result["recipes"][0]["scale"] == 2.0


# 8. Agent grocery list unit conversions
def test_agent_tool_unit_conversions():
    qty, unit, warning = convert_to_base("salt", 1, "tsp")
    assert round(qty, 2) == 6.04
    assert unit == "g"
    assert warning is None

    qty_l, unit_l, _ = convert_to_base("water", 1.5, "l")
    assert qty_l == 1500.0
    assert unit_l == "ml"


# 9. Item normalization helper test
def test_agent_tool_item_normalization():
    assert normalize_item("Potatoes ") == "potato"
    assert normalize_item("Onions") == "onion"
    assert normalize_item("Green Chillies") == "green chilli"
