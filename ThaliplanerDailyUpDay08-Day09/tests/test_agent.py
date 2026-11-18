"""Agent loop (S1) and LangGraph agent (S2) tested with a scripted fake LLM: no key, no internet."""
import json

import pytest
from fastapi.testclient import TestClient

import app.agent_loop as loop
import app.main as main
import app.tools as tools
from app.llm import LLMError

client = TestClient(main.app)

SEARCH = {"thought": "find recipes", "action": "search_recipes", "args": {"query": "moong dal khichdi"}}
BUILD = {"thought": "make the list", "action": "build_grocery_list",
         "args": {"selections": [{"recipe_id": 1, "servings": 8}, {"recipe_id": 3, "servings": 8}]}}


def final(text):
    return {"thought": "done", "action": "final_answer", "args": {"answer": text}}


class ScriptedLLM:
    """Returns the next scripted reply each time the agent asks, and records every prompt."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.prompts = []

    def __call__(self, system, user, json_mode=False, temperature=0.3):
        self.prompts.append(user)
        reply = self.replies.pop(0)
        return reply if isinstance(reply, str) else json.dumps(reply)


@pytest.fixture(autouse=True)
def no_vector_store(monkeypatch):
    """search_recipes falls back to keyword search, so no model or ChromaDB is needed."""
    def boom(*a, **k):
        raise RuntimeError("no vector store in tests")
    monkeypatch.setattr("app.vectorstore.search_chunks", boom, raising=False)


# ---------------- S1: hand-written loop ----------------
def test_search_recipes_returns_ids_and_falls_back():
    out = tools.search_recipes("moong dal")
    assert out["method"] == "keyword_fallback" and "note" in out
    assert out["results"][0]["id"] == 1 and out["results"][0]["has_quantities"] is True


def test_loop_search_then_build_then_answer(monkeypatch):
    llm = ScriptedLLM(SEARCH, BUILD, final("Here is your list."))
    monkeypatch.setattr(loop, "ask_llm", llm)
    result = loop.run_agent("Plan moong dal and khichdi for 8 people")
    assert [s["action"] for s in result["steps"]] == ["search_recipes", "build_grocery_list"]
    assert result["stopped"] == "final_answer" and result["answer"] == "Here is your list."
    moong = next(i for i in result["grocery_list"]["items"] if i["item"] == "moong dal")
    assert moong["quantity"] == 600
    assert "result:" in llm.prompts[1] and "Moong Dal" in llm.prompts[1]   # the model saw the observation


def test_loop_rejected_list_is_not_built(monkeypatch):
    monkeypatch.setattr(loop, "ask_llm", ScriptedLLM(BUILD, final("What would you like to change?")))
    result = loop.run_agent("list please", approve=lambda action: False)
    assert result["grocery_list"] is None
    assert "rejected" in result["steps"][0]["observation"]["error"]


def test_loop_survives_garbage_unknown_tool_and_bad_args(monkeypatch):
    replies = ["not json at all", {"action": "delete_database", "args": {}},
               {"action": "build_grocery_list", "args": {"selections": []}}, final("ok")]
    monkeypatch.setattr(loop, "ask_llm", ScriptedLLM(*replies))
    result = loop.run_agent("hello")
    assert [s["action"] for s in result["steps"]] == ["invalid", "invalid", "invalid"]
    assert result["answer"] == "ok"


def test_loop_tool_error_becomes_observation(monkeypatch):
    bad = {"action": "build_grocery_list", "args": {"selections": [{"recipe_id": 1, "servings": -2}]}}
    monkeypatch.setattr(loop, "ask_llm", ScriptedLLM(bad, final("sorry")))
    result = loop.run_agent("x")
    assert "positive number" in result["steps"][0]["observation"]["error"]
    assert result["grocery_list"] is None


def test_loop_stops_at_max_steps(monkeypatch):
    monkeypatch.setattr(loop, "ask_llm", ScriptedLLM(*[SEARCH] * 10))
    result = loop.run_agent("x", max_steps=3)
    assert result["stopped"] == "max_steps" and len(result["steps"]) == 3


def test_loop_empty_goal():
    with pytest.raises(ValueError):
        loop.run_agent("   ")


# ---------------- S2: LangGraph + POST /agent ----------------
@pytest.fixture
def fresh_graph(monkeypatch):
    import app.graph as graph
    monkeypatch.setattr(graph, "_graph", None)   # new InMemorySaver for each test
    return graph


def test_agent_pauses_for_approval_then_finishes(monkeypatch, fresh_graph):
    llm = ScriptedLLM(SEARCH, BUILD, final("Your list is ready."))
    monkeypatch.setattr(loop, "ask_llm", llm)

    first = client.post("/agent", json={"message": "Moong dal and khichdi for 8"}).json()
    assert first["status"] == "awaiting_approval" and first["answer"] == ""
    assert first["pending_approval"]["args"] == BUILD["args"]
    assert first["grocery_list"] is None                       # NOT built before approval
    assert len(llm.prompts) == 2                               # no LLM call while paused

    second = client.post("/agent", json={"thread_id": first["thread_id"], "approve": True}).json()
    assert second["status"] == "done" and second["answer"] == "Your list is ready."
    assert second["grocery_list"]["items"] and second["thread_id"] == first["thread_id"]


def test_agent_reject_path(monkeypatch, fresh_graph):
    monkeypatch.setattr(loop, "ask_llm", ScriptedLLM(BUILD, final("What should I change?")))
    first = client.post("/agent", json={"message": "list"}).json()
    done = client.post("/agent", json={"thread_id": first["thread_id"], "approve": False}).json()
    assert done["status"] == "done" and done["grocery_list"] is None
    assert done["answer"] == "What should I change?"


def test_agent_memory_across_turns(monkeypatch, fresh_graph):
    llm = ScriptedLLM(final("Moong dal takes 30 minutes."), final("It serves 4."))
    monkeypatch.setattr(loop, "ask_llm", llm)
    a = client.post("/agent", json={"message": "How long does moong dal take?"}).json()
    b = client.post("/agent", json={"thread_id": a["thread_id"], "message": "And how many does it serve?"}).json()
    assert b["turns_remembered"] == 2
    assert "How long does moong dal take?" in llm.prompts[1]   # turn 2 saw turn 1
    # a different thread has no memory
    llm.replies.append(final("ok"))
    c = client.post("/agent", json={"message": "hi"}).json()
    assert c["turns_remembered"] == 1 and "moong dal take" not in llm.prompts[2]


def test_agent_state_errors(monkeypatch, fresh_graph):
    monkeypatch.setattr(loop, "ask_llm", ScriptedLLM(BUILD, final("done")))
    assert client.post("/agent", json={"thread_id": "nope", "approve": True}).status_code == 409
    assert client.post("/agent", json={}).status_code == 400
    assert client.post("/agent", json={"message": "   "}).status_code == 400
    first = client.post("/agent", json={"message": "list"}).json()
    again = client.post("/agent", json={"thread_id": first["thread_id"], "message": "new question"})
    assert again.status_code == 409                            # must answer the approval first


def test_agent_llm_failure_is_502_and_thread_recovers(monkeypatch, fresh_graph):
    def boom(*a, **k):
        raise LLMError("GROQ_API_KEY is not set.")
    monkeypatch.setattr(loop, "ask_llm", boom)
    r = client.post("/agent", json={"message": "hi", "thread_id": "t1"})
    assert r.status_code == 502
    monkeypatch.setattr(loop, "ask_llm", ScriptedLLM(final("back again")))
    ok = client.post("/agent", json={"message": "hi", "thread_id": "t1"}).json()
    assert ok["status"] == "done" and ok["answer"] == "back again"


def test_agent_step_limit(monkeypatch, fresh_graph):
    monkeypatch.setattr(loop, "ask_llm", ScriptedLLM(*[SEARCH] * 20))
    body = client.post("/agent", json={"message": "loop forever"}).json()
    assert body["status"] == "done" and "allowed number of steps" in body["answer"]
    assert len(body["steps"]) == loop.MAX_STEPS
