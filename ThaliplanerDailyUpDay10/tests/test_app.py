"""Offline tests for ThaliPlanner: no API key, no internet, no model download."""
import json

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.chunking import chunk_documents, split_text
from app.llm import LLMError
from app.prompt_loader import PROMPTS_DIR, build_system_prompt
from app.rag import answer_question, should_abstain

client = TestClient(main.app)


# ---------- prompts ----------
def test_prompts_folder_is_lowercase_and_complete():
    assert PROMPTS_DIR.name == "prompts" and PROMPTS_DIR.is_dir()
    for name in ("system.md", "system_v1.md", "task_answer.md", "task_plan.md"):
        assert (PROMPTS_DIR / name).is_file()


def test_build_system_prompt_versions():
    assert "JSON" in build_system_prompt("v1", "answer")
    assert "TASK: Plan a thali" in build_system_prompt("v2", "plan")
    with pytest.raises(ValueError):
        build_system_prompt("v2", "nonsense")


# ---------- chunking ----------
def test_split_text_overlap_and_validation():
    chunks = split_text("word " * 500, chunk_size=100, overlap=20)
    assert len(chunks) > 1 and all(len(c) <= 100 for c in chunks)
    with pytest.raises(ValueError):
        split_text("abc", chunk_size=10, overlap=10)


def test_prompts_and_readme_are_not_indexed():
    sources = {c["metadata"]["source"] for c in chunk_documents()}
    assert not any(s.lower().startswith("prompt") for s in sources)
    assert "README.md" not in sources
    assert any(s.startswith("https://en.wikibooks.org") for s in sources)  # recipes are


# ---------- RAG ----------
def test_should_abstain():
    assert should_abstain("How many calories are in a Masala Dosa?")
    assert should_abstain("How much protein is in Moong Dal?")
    assert not should_abstain("Which dishes use moong dal?")


def test_abstain_answer_is_not_hardcoded_to_masala_dosa():
    out = answer_question("How many calories are in Khichdi?")
    assert out["abstained"] and out["citations"] == []
    assert out["answer"].startswith("I don't know.")
    assert "Masala Dosa" not in out["answer"]


def test_answer_with_fake_index(fake_index):
    assert fake_index.build_index() > 20
    out = answer_question("Which dishes can I make with moong dal?", top_k=5)
    assert not out["abstained"] and out["citations"]
    assert "Moong Dal" in out["answer"]


def test_rebuild_does_not_duplicate_and_stale_index_is_fixed(fake_index):
    first = fake_index.build_index()
    assert fake_index.build_index() == first          # rebuild, no duplicates
    assert fake_index.build_index(rebuild=False) == first  # upsert, no crash
    fake_index.get_collection().delete(ids=fake_index.get_collection().get()["ids"][:3])
    fake_index._index_checked = False
    assert fake_index.search_chunks("dhokla", top_k=3)  # detects mismatch, rebuilds
    assert fake_index.get_collection().count() == first


def test_search_chunks_validation(fake_index):
    assert fake_index.search_chunks("   ") == []
    with pytest.raises(ValueError):
        fake_index.search_chunks("x", top_k=0)


# ---------- API ----------
def test_basic_endpoints():
    assert client.get("/health").json() == {"status": "ok"}
    assert len(client.get("/records").json()) >= 20
    assert client.get("/records/13").json()["dish_name"] == "Paneer Butter Masala"
    assert client.get("/records/99999").status_code == 404
    assert client.get("/search", params={"q": "moong dal"}).json()[0]["dish_name"] == "Moong Dal"
    assert client.get("/search", params={"q": "  "}).status_code == 400


def test_ask_endpoint_abstains_for_nutrition():
    r = client.post("/ask", json={"question": "How many calories are in a Masala Dosa?"})
    assert r.status_code == 200 and r.json()["abstained"] is True
    assert client.post("/ask", json={"question": ""}).status_code == 422


def test_startup_does_not_need_heavy_packages():
    """Importing the API must not pull in chromadb / sentence-transformers."""
    import subprocess
    import sys
    code = ("import sys, app.main; "
            "bad = [m for m in ('app.vectorstore', 'app.embed', 'sentence_transformers', 'chromadb') if m in sys.modules]; "
            "print(bad)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         cwd=str(main.ROOT)).stdout.strip()
    assert out == "[]", out


# ---------- /chat ----------
def stub_llm(monkeypatch, reply):
    monkeypatch.setattr(main, "ask_llm", lambda *a, **k: reply)


def test_chat_valid_json(monkeypatch):
    stub_llm(monkeypatch, json.dumps({"answer": "35 minutes", "confidence": "HIGH", "follow_up": "Servings?"}))
    r = client.post("/chat", json={"question": "How long does Khichdi take?"})
    assert r.status_code == 200
    assert r.json() == {"answer": "35 minutes", "confidence": "high", "follow_up": "Servings?"}


@pytest.mark.parametrize("reply", ["not json", "[1, 2, 3]", '{"confidence": "high"}', "```json\n{broken\n```"])
def test_chat_bad_replies_fall_back_safely(monkeypatch, reply):
    stub_llm(monkeypatch, reply)
    r = client.post("/chat", json={"question": "hi"})
    assert r.status_code == 200 and r.json()["confidence"] == "low"


def test_chat_fenced_json_and_bad_confidence(monkeypatch):
    stub_llm(monkeypatch, '```json\n{"answer": "ok", "confidence": "very sure"}\n```')
    body = client.post("/chat", json={"question": "hi"}).json()
    assert body["answer"] == "ok" and body["confidence"] == "low" and body["follow_up"] == ""


def test_chat_errors_and_validation(monkeypatch):
    def boom(*a, **k):
        raise LLMError("GROQ_API_KEY is not set.")
    monkeypatch.setattr(main, "ask_llm", boom)
    assert client.post("/chat", json={"question": "hi"}).status_code == 502
    assert client.post("/chat", json={"question": "hi", "prompt_version": "v9"}).status_code == 422
    assert client.post("/chat", json={"question": "hi", "task": "x"}).status_code == 422
