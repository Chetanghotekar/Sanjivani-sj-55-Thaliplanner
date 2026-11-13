"""Day 4: FastAPI endpoints for ThaliPlanner."""
from pathlib import Path
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.records import load_records, get_by_id
from app.smart_search import smart_search

app = FastAPI(title="ThaliPlanner API", version="1.0.0")
ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_FILE = ROOT / "data" / "questions.json"

class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)

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
