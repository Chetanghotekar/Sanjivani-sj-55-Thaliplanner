# ThaliPlanner: Milestone Progress Tracker

Comprehensive development tracker for the ThaliPlanner Indian Culinary Assistant & Meal Planner project.

---

## Milestone Checklist (Days 1 – 14)

- [x] **Day 01: Project Foundation & Intro**
  - [x] Initialized workspace and Python virtual environment.
  - [x] Implemented baseline CLI menu generator (`day01_intro.py`, `day01_menu.py`).
  - [x] Configured Git version control and project structure.

- [x] **Day 02: Curated Dataset Creation**
  - [x] Authored 20 complete, verified starter Indian recipe records (`data/sample_records.py`).
  - [x] Covered key categories: Dals, Rice, Curries, South Indian, Chutneys, and Beverages.
  - [x] Stored metadata with servings, ingredients, timings, and Wikibooks source URLs.

- [x] **Day 03: HTML Ingestion Pipeline**
  - [x] Downloaded raw Wikibooks recipe pages into `data/raw/`.
  - [x] Implemented BeautifulSoup parsing pipeline (`app/ingest.py`) with noise filtering.
  - [x] Produced structured `data/records.json` dataset.

- [x] **Day 04: Structured Querying & Schema**
  - [x] Defined dataclass schema `Record` in `app/models.py`.
  - [x] Created database query utilities in `app/records.py` (`load_records`, `search`, `get_by_id`, `count_by`).
  - [x] Integrated unit tests for data integrity and schema validation.

- [x] **Day 05: Document Chunking with Metadata**
  - [x] Implemented boundary-aware text chunking (`app/chunking.py`).
  - [x] Preserved document provenance: source URL, page number, section title, and category.
  - [x] Filtered out project documentation from recipe knowledge to prevent hallucinations.

- [x] **Day 06: Dense Semantic Embeddings**
  - [x] Integrated `sentence-transformers/all-MiniLM-L6-v2` (`app/embed.py`).
  - [x] Generated 384-dimensional dense vectors for recipe text chunks.
  - [x] Implemented batch embedding with local model caching.

- [x] **Day 07: Persistent ChromaDB Vector Index**
  - [x] Configured persistent ChromaDB client (`app/vectorstore.py`).
  - [x] Configured Cosine similarity distance metric (`hnsw:space: "cosine"`).
  - [x] Created `search_chunks()` with score thresholding (`MIN_SCORE = 0.20`).

- [x] **Day 08: RAG Retrieval & Abstention Engine**
  - [x] Built retrieval-augmented answer generation in `app/rag.py`.
  - [x] Enforced responsible AI nutrition abstain policy (refuses to hallucinate calories).
  - [x] Formatted responses with numbered citations and verified Wikibooks links.

- [x] **Day 09: Ingredient Scaling & Unit Normalization**
  - [x] Authored ingredient density and unit conversion matrix in `app/tools.py`.
  - [x] Implemented `build_grocery_list()` scaling recipes to target servings.
  - [x] Created ingredient name normalization (`normalize_item`) to collapse duplicates.

- [x] **Day 10: LangGraph Conversational Agent**
  - [x] Built stateful LangGraph agent graph (`app/agent.py`).
  - [x] Designed multi-day meal planner with dietary preference filters (vegan, regional).
  - [x] Implemented consecutive dal repetition detection and replacement loops.

- [x] **Day 11: Production FastAPI Backend & Test Harness**
  - [x] Developed FastAPI application (`app/main.py`) with `/health`, `/ask`, `/records`, `/agent`.
  - [x] Wrote automated test suite (`tests/test_day11.py`) validating all core functionality.
  - [x] Configured CORS middleware and request validation schemas.

- [x] **Day 12: Web UI, Dockerization & Cloud Deployment**
  - [x] Created interactive Streamlit frontend (`ui/app.py`).
  - [x] Developed standalone fallback UI dashboard (`app/ui_html.py`).
  - [x] Created production `Dockerfile` with CPU-optimized PyTorch and `docker-compose.yml`.
  - [x] Created `render.yaml` infrastructure configuration for cloud deployment.

- [x] **Day 13: Production Hardening, Caching & Performance Notes**
  - [x] Implemented in-memory LRU cache (`_RAG_CACHE`) achieving $\approx 0.18\text{ ms}$ query latency.
  - [x] Added prompt-injection security guardrails (`is_prompt_injection()`) and 500-char input limit.
  - [x] Added real-time latency and token metrics logging to `/ask`.
  - [x] Documented system architecture with Mermaid diagram and benchmarks in `README.md`.
  - [x] Authored professional portfolio summary in `docs/resume.md`.

- [x] **Day 14: Technical Interview Prep & Final Release**
  - [x] Authored comprehensive technical interview guide (`docs/interview.md`).
  - [x] Formulated 60-second elevator pitch and STAR-format hardest problem story.
  - [x] Detailed answers for 10 likely senior engineering interview questions.
  - [x] Verified 14/14 automated tests passing and zero Ruff lint errors.
  - [x] Tagged repository as `final` release.

---

## Verification & Test Summary

| Metric | Result | Target | Status |
| :--- | :--- | :--- | :--- |
| **Automated Tests** | 14 / 14 Passed | $\ge 13$ | ✅ Passed |
| **Ruff Linting** | 0 Errors | 0 Errors | ✅ Clean |
| **Cache Latency** | 0.18 ms | $\le 1.0\text{ ms}$ | ✅ Optimal |
| **Prompt Injection Defense** | 100% Block Rate | 100% | ✅ Protected |
| **Nutrition Abstain** | 100% Precision | 100% | ✅ Responsible AI |
| **Docker Build** | CPU-optimized | Lightweight | ✅ Ready |
