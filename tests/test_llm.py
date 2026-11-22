"""app/llm.py with requests.post faked."""
import pytest

import app.llm as llm


class Fake:
    def __init__(self, data, status=200):
        self._d, self.status_code, self.text = data, status, str(data)

    def json(self):
        return self._d


def test_groq_ok(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "real")
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: Fake({"choices": [{"message": {"content": "hi"}}]}))
    assert llm.ask_llm("s", "u", json_mode=True) == "hi"


def test_gemini_ok(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "real")
    monkeypatch.setattr(llm.requests, "post",
                        lambda *a, **k: Fake({"candidates": [{"content": {"parts": [{"text": "yo"}]}}]}))
    assert llm.ask_llm("s", "u") == "yo"


@pytest.mark.parametrize("key", ["", "your_groq_key_here"])
def test_missing_or_placeholder_key(monkeypatch, key):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", key)
    with pytest.raises(llm.LLMError):
        llm.ask_llm("s", "u")


def test_bad_provider_http_error_and_bad_shape(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    with pytest.raises(llm.LLMError):
        llm.ask_llm("s", "u")
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "real")
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: Fake({"error": "rate"}, 429))
    with pytest.raises(llm.LLMError):
        llm.ask_llm("s", "u")
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: Fake({"unexpected": 1}))
    with pytest.raises(llm.LLMError):
        llm.ask_llm("s", "u")
