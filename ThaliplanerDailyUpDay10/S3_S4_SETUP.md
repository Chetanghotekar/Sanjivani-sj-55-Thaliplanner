# ThaliPlanner S1/S2 RAG + Evaluation setup

Merge these files into the existing `ThaliplanerDailyUp` project. Do not replace the entire `app/` folder; keep existing modules such as `llm.py`, `prompt_loader.py`, `records.py`, and `smart_search.py`.

> Prompts live in the lower-case `prompts/` folder. After changing what gets indexed (chunking), rebuild the index (`python -m app.vectorstore`) and re-run `python -m eval.run_eval`; the numbers in `eval/eval_results.md` change.

## Files included

- `app/rag.py`: chunk retrieval, grounded extractive response, numbered source citations, and explicit abstention for nutrition questions/Q6.
- `app/main.py`: adds `POST /ask` while retaining the existing endpoints.
- `app/chunking.py`: supports configurable chunk size and overlap for experiments; defaults remain 900/120.
- `eval/eval_set.json`: 15 evaluation rows, including the required unanswerable calorie question.
- `eval/run_eval.py`: compares two chunk-size/top-k configurations, writes `eval/eval_results.md`, and updates the winner table in `README.md`.

## Run in PowerShell from project root

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app.chunking
python -m app.vectorstore
python -m uvicorn app.main:app --reload
```

In another terminal (same project and virtual environment), run the evaluation:

```powershell
python -m eval.run_eval
```

Expected final messages:

```text
Evaluation complete: eval/eval_results.md
README updated with winner table. Winner: Config ... (...%)
```

The winning configuration and score are generated from the actual local embeddings and documents; they are not hard-coded. First run may download `sentence-transformers/all-MiniLM-L6-v2` and needs internet access.

## Test POST /ask

Open `http://127.0.0.1:8000/docs`, find `POST /ask`, and submit:

```json
{"question": "Which dishes can I make with moong dal?", "top_k": 5}
```

The response includes `answer`, `citations`, and `abstained`. For Q6:

```json
{"question": "How many calories are in a Masala Dosa?", "top_k": 5}
```

The answer must start with `I don't know.` and return an empty citation list.
