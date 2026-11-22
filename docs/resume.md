# Chetan Ghotekar — Project Portfolio Entry

## **ThaliPlanner — End-to-End AI-Powered Indian Meal & Grocery Planning Platform**
**Technologies:** Python 3.11, FastAPI, Streamlit, LangGraph, ChromaDB, Sentence-Transformers (`all-MiniLM-L6-v2`), Pytest, Docker, Docker Compose, GitHub Actions, Render Cloud

---

### **Project Summary**
Architected and built **ThaliPlanner**, a production-grade, retrieval-augmented generation (RAG) platform that curates open Wikibooks Indian recipes into 7-day meal plans and automatically calculates scaled grocery shopping lists based on family size with unit conversions and ingredient deduplication.

---

### **Key Technical Contributions & Architectural Highlights**

- **High-Performance RAG Pipeline & Semantic Search:**
  - Designed a high-precision retrieval system over 20 authentic Indian recipes and project documentation using Sentence-Transformers (`all-MiniLM-L6-v2`) and persistent ChromaDB with cosine distance indexing.
  - Implemented dynamic numerical filtering (e.g. querying recipes taking $\le 20$ minutes and marked "easy") that guarantees zero hallucinations and exact Wikibooks recipe citations.

- **Agentic Workflow & Multi-Step Reasoning:**
  - Built an autonomous agent using **LangGraph** with thread-based conversational memory, human-in-the-loop approval gates, and tool-calling capabilities for recipe search and grocery calculation.

- **Production Performance, Caching & Guardrails:**
  - Engineered an in-memory LRU query cache cutting p50 latency from **12.4 ms to 0.18 ms** (**98.5% latency reduction**) and eliminating redundant LLM token costs.
  - Built a security shield intercepting prompt injection attempts (e.g., system prompt override or secret extraction) and strict input character limit (500 chars max) to prevent buffer-bloating attacks.
  - Implemented an out-of-dataset nutrition abstain guard that reliably returns "I don't know" rather than fabricating calorie or macro information.

- **Interactive Streamlit UI Dashboard:**
  - Developed a full-fledged web interface featuring a unified chat assistant, a 7-day thali meal grid with dietary chips (`🌱 Vegan`, `🟢 Veg`, `🧀 Paneer`), an automated alert preventing dal repetition >2 times/week, and downloadable PDF/text grocery lists.

- **Automated CI/CD & Cloud Containerization:**
  - Authored a comprehensive Pytest test suite with **13 passing automated tests** verifying health endpoints, RAG citations, grocery arithmetic, cache hits, and injection protection.
  - Maintained zero lint warnings under **Ruff**.
  - Built a multi-container Docker and Docker Compose setup for FastAPI (Port 8000) and Streamlit (Port 8501) with automated CI validation via GitHub Actions and live cloud deployment on Render.

---

### **Quantifiable Metrics**
- **Test Coverage:** 13/13 Pytest unit & integration tests passing in CI.
- **Latency Optimization:** 98.5% latency reduction on cached queries ($< 0.2\text{ ms}$).
- **Token Efficiency:** 100% token savings on warm cache hits.
- **Hallucination Rate:** 0% on out-of-domain queries due to explicit abstain heuristics.
