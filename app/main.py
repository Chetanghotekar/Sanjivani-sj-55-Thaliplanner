"""Day 4-9: FastAPI endpoints for ThaliPlanner (adds /chat, /search/semantic, /ask and /agent)."""
from pathlib import Path
from typing import Literal
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError
from app.records import load_records, get_by_id
from app.smart_search import smart_search
from app.llm import ask_llm, LLMError
from app.prompt_loader import build_system_prompt
from app.rag import answer_question

# NOTE: app.vectorstore (ChromaDB + sentence-transformers) and app.graph (LangGraph)
# are imported inside the endpoints that need them, so the API starts quickly and /chat, /search and
# /records work even before those heavy packages are installed.

app = FastAPI(title="ThaliPlanner API", version="3.0.0")
ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_FILE = ROOT / "data" / "questions.json"


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)


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


@app.get("/")
def home():
    return "Welcome to Thaliplanner"


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
            f'ingredients: {", ".join(r.get("ingredients") or [])}'
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
    if not isinstance(data, dict):
        raise ValueError("JSON reply is not an object")
    confidence = str(data.get("confidence", "")).strip().lower()
    data["confidence"] = confidence if confidence in {"high", "medium", "low"} else "low"
    data["follow_up"] = data.get("follow_up") or ""
    return ChatResponse(**data)


def run_chat(question: str, task: str = "answer", prompt_version: str = "v2") -> ChatResponse:
    """Shared by POST /chat and eval/run_compare.py."""
    system = build_system_prompt(prompt_version, task)
    user = f"RECIPE CONTEXT:\n{_context_text(question)}\n\nUSER QUESTION:\n{question.strip()}"
    raw = ask_llm(system, user, json_mode=True)
    try:
        return _parse_json_reply(raw)
    except (ValueError, ValidationError):  # json.JSONDecodeError is a ValueError
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
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"Prompt file missing: {exc.filename}")


@app.get("/search/semantic")
def semantic_search_records(q: str, limit: int = 5):
    """Semantic search over persistent ChromaDB document chunks."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 50")
    try:
        from app.vectorstore import search_chunks
        results = search_chunks(q, top_k=limit)
        return {"query": q, "count": len(results), "results": results}
    except (ImportError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/ask")
def ask(request: AskRequest):
    """Answer from retrieved ThaliPlanner chunks and return source citations."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    try:
        return answer_question(request.question, top_k=request.top_k)
    except (ImportError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))


class AgentRequest(BaseModel):
    message: str | None = Field(default=None, max_length=1000)
    thread_id: str | None = Field(default=None, max_length=100)
    approve: bool | None = None


class AgentResponse(BaseModel):
    thread_id: str
    status: Literal["awaiting_approval", "done"]
    answer: str = ""
    pending_approval: dict | None = None
    grocery_list: dict | None = None
    steps: list[dict] = []
    turns_remembered: int = 0


@app.post("/agent", response_model=AgentResponse)
def agent(request: AgentRequest):
    """LangGraph agent with memory (per thread_id) and one approval step.

    1) Send {"message": "..."}. If the agent wants to build a shopping list it pauses
       and returns status "awaiting_approval" with the recipes and servings it chose.
    2) Send {"thread_id": "...", "approve": true} (or false) to continue.
    3) Send another {"thread_id": "...", "message": "..."} for a follow-up that remembers the chat.
    """
    if request.message is None and request.approve is None:
        raise HTTPException(status_code=400, detail="Send a message, or approve true/false")
    try:
        from app.graph import AgentStateError, run_turn
    except ImportError:
        raise HTTPException(status_code=503, detail="langgraph is not installed. Run: pip install -r requirements.txt")
    try:
        return run_turn(request.message, request.thread_id, request.approve)
    except AgentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
