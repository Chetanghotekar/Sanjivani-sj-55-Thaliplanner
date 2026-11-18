# ThaliPlanner

ThaliPlanner is a beginner-friendly Indian recipe data and search project.

## Project structure
- `day01_intro.py`, `day01_menu.py`: Day 1 introduction and menu
- `data/sample_records.py`: Day 2 sample recipe records
- `app/records.py`, `app/cli.py`: Day 2 record operations and CLI; updated in Day 3/4 to load JSON
- `app/fetch.py`, `app/models.py`, `app/ingest.py`: Day 3 data pipeline
- `app/main.py`, `app/smart_search.py`: Day 4 FastAPI and smart search
- `analysis/explore.py`: Day 4 Pandas analysis
- `data/raw/`: downloaded source HTML
- `data/records.json`: cleaned recipe records

## Setup (Windows)
```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run Day 1
```bash
python day01_intro.py
python day01_menu.py
```

## Run Day 2 CLI / Day 3 records
```bash
python -m app.cli
```

## Run Day 3 pipeline
```bash
python -m app.fetch
python -m app.ingest
```
Fetch downloads the configured Wikibooks pages into `data/raw/`. Ingest extracts recipe sections where possible and saves normalized records to `data/records.json`. The parser is best-effort because Wikibooks page layouts vary; inspect the output and correct any missing ingredient/serving details using the source page. It does not invent missing values.

## Run Day 4 analysis
```bash
python -m analysis.explore
```

## Run Day 4 API
```bash
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs

## Git
```bash
git add .
git commit -m "Complete ThaliPlanner Days 1-4"
git push origin main
```
Do not commit `.venv/`, `.env` or `chroma_db/`. Empty folders are not tracked by Git.

## Day 5: docs and evaluation questions
- `docs/how_llms_work.md` (+ `docs/llm_flow.svg`, the diagram): how an LLM works
- `eval/questions.md`: 10 real ThaliPlanner user questions (Q6 cannot be answered from the data)

## Day 6: LLM chat (`POST /chat`)
1. Copy `.env.example` to `.env` and add your Groq or Gemini key. `.env` is git-ignored: never commit it.
2. Start the API (see "Run the API" below) and open `/docs`, then try `POST /chat`:
```json
{"question": "How long does Khichdi take?", "task": "answer", "prompt_version": "v2"}
```
It returns `{"answer": "...", "confidence": "high|medium|low", "follow_up": "..."}`.
- `app/llm.py`: provider wrapper (Groq / Gemini, chosen by `LLM_PROVIDER`)
- `prompts/`: `system.md`, `system_v1.md`, `task_answer.md`, `task_plan.md` (folder name is lower-case)
- `python -m eval.run_compare` runs 10 questions through prompt v1 and v2 and fills `eval/prompt_compare.md`

## Day 7: chunking, embeddings, ChromaDB
- `app/chunking.py`: splits recipes, `docs/` and `data/raw/` into chunks with source / page / title
- `app/embed.py`: sentence-transformers embeddings (`all-MiniLM-L6-v2`) and `python -m app.embed` search report
- `app/vectorstore.py`: persistent ChromaDB index in `chroma_db/` (git-ignored, rebuilt on demand)
- `GET /search/semantic?q=...`

## Day 8: RAG with citations (`POST /ask`)
- `app/rag.py`: answers only from retrieved chunks, returns numbered citations, and says "I don't know" for nutrition questions or weak matches
- `python -m eval.run_eval` compares two chunk-size / top-k settings on `eval/eval_set.json` and updates the table below

## Run the API
```bash
python -m pip install -r requirements.txt
python -m app.vectorstore          # build the ChromaDB index (first run downloads the embedding model)
python -m uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs. Run the tests (no API key or internet needed) with `python -m pytest tests`.

<!-- RETRIEVAL_EVAL_START -->
## Retrieval configuration experiment

`python -m eval.run_eval` compares two chunk-size/top-k configurations on all 15 rows in `eval/eval_set.json`. A row passes when all expected evidence terms appear in the retrieved top-k chunks; Q6 passes only when the system is configured to abstain. Term recall is the fraction of expected evidence checks found (Q6 abstention counts as one check).

| Configuration | Chunk size | Overlap | Top-k | Chunks | Questions passed | Accuracy | Evidence / abstention recall |
|---|---:|---:|---:|---:|---:|---:|---:|
| Config A | 700 | 100 | 3 | 57 | 10/15 | 66.7% | 76.2% |
| Config B | 900 | 120 | 5 | 49 | 11/15 | 73.3% | 78.6% |

**Winner: Config B** (highest question-level accuracy: 73.3%).

<!-- RETRIEVAL_EVAL_END -->
