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
