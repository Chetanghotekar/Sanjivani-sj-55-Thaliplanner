"""Day 4 + Day 6: FastAPI endpoints for ThaliPlanner (adds POST /chat)."""
from pathlib import Path
from typing import Literal
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError
from app.records import load_records, get_by_id
from app.smart_search import smart_search
from app.llm import ask_llm, LLMError
from app.prompt_loader import build_system_prompt

app = FastAPI(title="ThaliPlanner API", version="2.0.0")
ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_FILE = ROOT / "data" / "questions.json"


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    task: Literal["answer", "plan"] = "answer"
    prompt_version: Literal["v1", "v2"] = "v2"


class ChatResponse(BaseModel):
    answer: str
    confidence: Literal["high", "medium", "low"]
    follow_up: str = ""


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/records")
def list_records(limit: int = 100):
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")
    return load_records()[:limit]


@app.get("/records/{record_id}")
def record_detail(record_id: int):
    record = get_by_id(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return record


@app.get("/search")
def search_records(q: str, limit: int = 10):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    return smart_search(q, limit)


@app.post("/questions")
def save_question(request: QuestionRequest):
    QUESTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    questions = []
    if QUESTIONS_FILE.exists():
        try:
            questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            questions = []
    questions.append({"question": request.question.strip()})
    QUESTIONS_FILE.write_text(json.dumps(questions, indent=2), encoding="utf-8")
    return {"message": "Question saved", "total_questions": len(questions)}


def _context_text(question: str, limit: int = 3) -> str:
    """Top matching recipes from Day 4 smart search, formatted for the prompt."""
    hits = smart_search(question, limit)
    if not hits:
        return "No matching recipes found."
    lines = []
    for r in hits:
        lines.append(
            f'- {r.get("dish_name")} ({r.get("region_or_type")}); servings: {r.get("servings")}; '
            f'time/difficulty: {r.get("time_and_difficulty")}; '
            f'ingredients: {", ".join(r.get("ingredients", []))}'
        )
    return "\n".join(lines)


def _parse_json_reply(raw: str) -> ChatResponse:
    """Parse the model reply into the response schema, tolerating ```json fences."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found")
    data = json.loads(text[start:end + 1])
    if str(data.get("confidence", "")).lower() not in {"high", "medium", "low"}:
        data["confidence"] = "low"
    data["confidence"] = str(data["confidence"]).lower()
    data["follow_up"] = data.get("follow_up") or ""
    return ChatResponse(**data)


def run_chat(question: str, task: str = "answer", prompt_version: str = "v2") -> ChatResponse:
    """Shared by POST /chat and eval/run_compare.py."""
    system = build_system_prompt(prompt_version, task)
    user = f"RECIPE CONTEXT:\n{_context_text(question)}\n\nUSER QUESTION:\n{question.strip()}"
    raw = ask_llm(system, user, json_mode=True)
    try:
        return _parse_json_reply(raw)
    except (ValueError, json.JSONDecodeError, ValidationError):
        # Safe fallback so the API always returns the promised JSON shape.
        return ChatResponse(answer=raw.strip()[:1000], confidence="low",
                            follow_up="Could you rephrase your question?")


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    try:
        return run_chat(request.question, request.task, request.prompt_version)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
