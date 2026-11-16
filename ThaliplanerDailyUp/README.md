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
Do not commit `.venv/`. Empty folders are not tracked by Git.

## S1: Retrieval-augmented question answering

The `POST /ask` endpoint retrieves relevant document chunks and returns an extractive answer with numbered citations. Every citation includes the source, title, page, and similarity score. Questions asking for nutrition facts (including Q6 about Masala Dosa calories) return **I don't know** because the recipe dataset has no nutrition fields.

Run the API:

```powershell
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`, select `POST /ask`, and try:

```json
{"question": "Which dishes can I make with moong dal?", "top_k": 5}
```

Q6 abstention check:

```json
{"question": "How many calories are in a Masala Dosa?", "top_k": 5}
```

Expected answer begins with `I don't know.`

## S2: 15-question retrieval evaluation

The evaluation dataset is `eval/eval_set.json` (15 rows). Run both retrieval configurations and automatically write the measured comparison and winner into this README:

```powershell
python -m eval.run_eval
```

Detailed per-question results are saved to `eval/eval_results.md`. The script compares chunk size/overlap and top-k, checks the expected evidence terms, and treats Q6 as correct only when the RAG system abstains. The winner below is filled in by the evaluation run; do not manually guess the winning configuration.

<!-- RETRIEVAL_EVAL_START -->
## Retrieval configuration experiment

Run `python -m eval.run_eval` to populate the measured winner table here.
<!-- RETRIEVAL_EVAL_END -->
