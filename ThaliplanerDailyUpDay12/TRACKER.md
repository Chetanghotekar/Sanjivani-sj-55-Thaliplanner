# ThaliPlanner — Project Submission Tracker

| Field | Submission Details |
| :--- | :--- |
| **Project Name** | ThaliPlanner — Plan • Cook • Enjoy |
| **Participant / Team** | Chetan Ghotekar (Sanjivani) |
| **GitHub Repository** | [https://github.com/Chetanghotekar/Sanjivani-sj-55-Thaliplanner.git](https://github.com/Chetanghotekar/Sanjivani-sj-55-Thaliplanner.git) |
| **Feature Branch** | `feature/day12-deployment` |
| **Pull Request (Merged)**| Merged into `main` after all CI checks green |
| **CI Workflow** | GitHub Actions (`.github/workflows/ci.yml`) — Ruff, Pytest, Docker Build |
| **Live App URL (Render)** | [https://sanjivani-thaliplanner-ui.onrender.com](https://sanjivani-thaliplanner-ui.onrender.com) |
| **Live Public `/health` URL** | [https://sanjivani-thaliplanner-api.onrender.com/health](https://sanjivani-thaliplanner-api.onrender.com/health) |
| **Live API Swagger Docs** | [https://sanjivani-thaliplanner-api.onrender.com/docs](https://sanjivani-thaliplanner-api.onrender.com/docs) |
| **Hugging Face Space** | [https://huggingface.co/spaces/Chetanghotekar/ThaliPlanner](https://huggingface.co/spaces/Chetanghotekar/ThaliPlanner) |

---

## Public Health Check Response
Sending a GET request to `https://sanjivani-thaliplanner-api.onrender.com/health` returns:
```json
{
  "status": "ok"
}
```

---

## Daily Milestone Completion Summary

| Day | Feature / Deliverable | Status | Verification Details |
| :---: | :--- | :---: | :--- |
| **Day 1** | Python Intro & Menu logic | ✅ Completed | `day01_intro.py`, `day01_menu.py` |
| **Day 2** | 20 Recipe Schema & CLI | ✅ Completed | `data/sample_records.py`, `app/records.py`, `app/cli.py` |
| **Day 3** | Data Ingestion Pipeline & Normalization | ✅ Completed | `app/fetch.py`, `app/ingest.py`, `data/records.json` |
| **Day 4** | FastAPI API & Smart Search | ✅ Completed | `app/main.py`, `app/smart_search.py`, `analysis/explore.py` |
| **Day 5** | LLM Architecture Docs & Questions | ✅ Completed | `docs/how_llms_work.md`, `eval/questions.md` |
| **Day 6** | Multi-Provider LLM Chat (`/chat`) | ✅ Completed | `app/llm.py`, `prompts/`, `eval/prompt_compare.md` |
| **Day 7** | Semantic Chunking, Embeddings & ChromaDB | ✅ Completed | `app/chunking.py`, `app/embed.py`, `app/vectorstore.py` |
| **Day 8** | RAG with Citations & Grocery Tool | ✅ Completed | `app/rag.py` (`/ask`), `app/tools.py` (`build_grocery_list`) |
| **Day 9** | LangGraph Agent with Approval Step | ✅ Completed | `app/graph.py` (`POST /agent`), `app/agent_loop.py` |
| **Day 10** | Unified Streamlit Dashboard UI | ✅ Completed | `ui/app.py` (Chat, 7-Day Grid, Grocery list, Dietary chips) |
| **Day 11** | Test Suite (10 Pytest) & Dockerization | ✅ Completed | `tests/test_day11.py`, `Dockerfile`, `docker-compose.yml` |
| **Day 12** | GitHub Actions CI & Cloud Deployment | ✅ Completed | `.github/workflows/ci.yml`, `render.yaml`, Live URL & `/health` |

---

## Deployment Configuration (`render.yaml`)
```yaml
services:
  - type: web
    name: sanjivani-thaliplanner-api
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    autoDeploy: true
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: HF_HUB_OFFLINE
        value: "1"

  - type: web
    name: sanjivani-thaliplanner-ui
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: streamlit run ui/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
    autoDeploy: true
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
```
