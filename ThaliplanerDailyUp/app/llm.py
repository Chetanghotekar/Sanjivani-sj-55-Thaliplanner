"""Day 6: Small provider wrapper so the rest of the app never touches Groq/Gemini directly. """
import os
import requests
from dotenv import load_dotenv

load_dotenv()  # reads .env (never committed); .env.example shows the needed keys

TIMEOUT_SECONDS = 30


class LLMError(Exception):
    """Raised when the provider is misconfigured or the API call fails."""


def _groq(system: str, user: str, json_mode: bool, temperature: float) -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise LLMError("GROQ_API_KEY is not set. Copy .env.example to .env and add your key.")
    payload = {
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json=payload,
        timeout=TIMEOUT_SECONDS,
    )
    if resp.status_code != 200:
        raise LLMError(f"Groq error {resp.status_code}: {resp.text[:300]}")
    return resp.json()["choices"][0]["message"]["content"]


def _gemini(system: str, user: str, json_mode: bool, temperature: float) -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise LLMError("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    config = {"temperature": temperature}
    if json_mode:
        config["responseMimeType"] = "application/json"
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": key},
        json={
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": config,
        },
        timeout=TIMEOUT_SECONDS,
    )
    if resp.status_code != 200:
        raise LLMError(f"Gemini error {resp.status_code}: {resp.text[:300]}")
    try:
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise LLMError(f"Unexpected Gemini response shape: {exc}") from exc


PROVIDERS = {"groq": _groq, "gemini": _gemini}


def ask_llm(system: str, user: str, json_mode: bool = False, temperature: float = 0.3) -> str:
    """Send one system + user message to the provider chosen by LLM_PROVIDER."""
    provider = os.getenv("LLM_PROVIDER", "groq").lower().strip()
    if provider not in PROVIDERS:
        raise LLMError(f"Unknown LLM_PROVIDER '{provider}'. Use one of: {', '.join(PROVIDERS)}")
    try:
        return PROVIDERS[provider](system, user, json_mode, temperature)
    except requests.RequestException as exc:
        raise LLMError(f"Network error calling {provider}: {exc}") from exc
