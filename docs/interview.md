# ThaliPlanner: Technical Interview Guide & 60-Second Pitch

---

## 1. The 60-Second ThaliPlanner Pitch

> **"ThaliPlanner is an intelligent, production-ready Indian culinary assistant and meal planning platform powered by Hybrid RAG and LangGraph agents.**
>
> While standard recipe chatbots hallucinate measurements, fail at numerical filtering (like finding dishes under 20 minutes), and break when scaling ingredient units, ThaliPlanner combines **deterministic structured metadata extraction** from open-source Wikibooks with **dense semantic vector retrieval using ChromaDB**.
>
> On top of that, an autonomous **LangGraph agent** orchestrates multi-day thali balancing, dietary constraints (vegan, South Indian, dal alternation), and calculates a **consolidated, scaled grocery list** with automated metric/volume unit conversions.
>
> Built with **FastAPI**, **Streamlit**, an **in-memory LRU cache** delivering sub-millisecond cached queries, a **prompt-injection security shield**, and containerized via **Docker** with **100% automated CI test coverage**, ThaliPlanner bridges the gap between conversational AI and deterministic, production-grade food planning."

---

## 2. Hardest Problem Story: Solving RAG Quantitative Filtering & Unit Chaos (STAR Method)

### **Situation**
During the initial deployment of ThaliPlanner's RAG pipeline, users asked questions like *"Which recipes are easy and take 20 minutes or less?"* and *"Scale Moong Dal for 8 people."* 
Pure semantic vector search (`sentence-transformers` + ChromaDB) returned dishes like *Indian Rice (25 min)*, *Cholley (60 min)*, and *Mango Chutney (35 min)* simply because the words "minutes" and "easy" appeared in their embeddings. Furthermore, scaling recipes across varied units like *"cups"*, *"tbsp"*, *"tsp"*, and *"pieces"* caused inaccurate conversions or duplicate grocery items.

### **Task**
I had to eliminate semantic retrieval hallucination for quantitative attributes (time, servings, difficulty) while providing an accurate mathematical scaling engine that normalizes irregular ingredient units into precise metric weights ($g, ml$) without degrading response latency.

### **Action**
1. **Hybrid Retrieval Routing:** In `app/rag.py`, I separated quantitative queries from open-ended semantic queries. I implemented regex-based numerical time parsing (`_parse_time_and_difficulty()`) and structured filtering over `records.json` before hitting the vector store.
2. **Ingredient Normalization & Conversion Engine:** In `app/tools.py`, I constructed a deterministic unit conversion matrix (`DIRECT_UNITS`, `VOLUME_ML`, `GRAMS_PER_CUP`, `PIECE_GRAMS`) with text stemming (`normalize_item`) to collapse ingredients like *"Potatoes"* and *"potato"* into a unified entity with exact scaled grams.
3. **Guardrails & In-Memory LRU Cache:** Added regex-based prompt-injection filters and an LRU cache (`_RAG_CACHE`) with latency and token tracking.

### **Result**
- **100% precision on numerical queries:** Queries for $\le 20$ minutes accurately return only Masala Chai I (10m), Coconut Chutney (15m), and Onion Chutney (20m) in ascending order.
- **Zero unit conversion errors:** All grocery quantities correctly sum up (e.g. 8 servings of Moong Dal scales to exactly 400g).
- **Sub-millisecond latency:** Repeated queries return in $\approx 0.18\text{ ms}$ with zero LLM cost.
- **14/14 automated unit tests passing** continuously in GitHub Actions CI.

---

## 3. Top 10 Technical Interview Questions & Answers

### **Q1: What is the high-level architecture of ThaliPlanner?**
**Answer:**  
ThaliPlanner follows a decoupled, service-oriented architecture:
- **Data Ingestion (`app/ingest.py`):** Parses raw Wikibooks HTML into validated JSON records matching the `Record` dataclass schema.
- **Vector Store & Chunking (`app/vectorstore.py`, `app/chunking.py`):** Uses ChromaDB with cosine similarity and `sentence-transformers/all-MiniLM-L6-v2` embeddings for dense retrieval.
- **RAG & Guardrails (`app/rag.py`):** Implements hybrid retrieval, an LRU query cache, token/latency logging, a prompt-injection shield, and a strict nutrition abstain policy.
- **Agent Orchestrator (`app/agent.py`, `app/tools.py`):** A LangGraph state machine coordinating multi-step meal planning, recipe selection, and grocery aggregation.
- **Serving Layer (`app/main.py` & `ui/app.py`):** FastAPI backend exposing `/health`, `/ask`, `/records`, `/agent` alongside a responsive Streamlit web dashboard.

---

### **Q2: Why use Cosine similarity over Euclidean (L2) distance for recipe embeddings?**
**Answer:**  
Recipe document chunks vary significantly in length—some have 3 ingredients while others have 15 ingredients and detailed multi-paragraph methods. Euclidean distance is sensitive to vector magnitude (length of the text), whereas **Cosine similarity measures the angle between vectors**, capturing semantic orientation independent of document length. This prevents short recipe chunks from being penalized simply because they contain fewer tokens.

---

### **Q3: When and why does ThaliPlanner abstain from answering?**
**Answer:**  
To prevent hallucinations and comply with responsible AI principles, ThaliPlanner has a strict **abstain policy**:
1. **Nutrition & Calorie Questions:** The Wikibooks dataset does not contain validated macronutrient/calorie data. If a user asks *"How many calories are in Idli?"*, the system detects keywords (`calories`, `protein`, `macros`) and immediately returns:  
   *"I don't know. The available ThaliPlanner recipe data does not contain calorie or nutrition information."*
2. **Low-Similarity Retrieval:** If the cosine similarity score of the top-ranked vector search chunk falls below `MIN_SCORE = 0.20`, the system abstains rather than inventing recipe instructions.

---

### **Q4: How does ThaliPlanner protect against prompt injection?**
**Answer:**  
Before a query reaches semantic search or an LLM call, it passes through `is_prompt_injection()` in `app/rag.py`. It evaluates the prompt against known adversarial patterns (e.g., *"ignore previous instructions"*, *"system override"*, *"reveal system prompt"*, *"developer mode"*, *"drop table"*).  
Furthermore, `MAX_QUESTION_LENGTH = 500` enforces an input length ceiling to prevent buffer-bloating attacks. If an attack is detected, the query is blocked with an explicit warning log and the system returns a safe abstention.

---

### **Q5: How does the LangGraph agent prevent repetitive dishes in weekly meal plans?**
**Answer:**  
The agent graph maintains conversation and planning state. When generating a multi-day thali schedule, a validation node inspects the selected lentils and curries across consecutive days. If a duplicate dal (e.g., Moong Dal two days in a row) is detected, the graph triggers a corrective loop, swapping in an alternate protein source (e.g., Langar Dal or Cholley) before finalizing the thali.

---

### **Q6: How does the ingredient grocery scaling handle mixed measurement units?**
**Answer:**  
In `app/tools.py`, ingredient scaling relies on a multi-stage conversion pipeline:
1. **Identity & Direct Units:** Grams and milliliters scale linearly ($x \times \text{scale}$).
2. **Volume-to-Weight Mapping:** Using `GRAMS_PER_CUP` and `VOLUME_ML`, volumetric measurements (cups, tablespoons, teaspoons) are converted into density-adjusted grams (e.g., 1 cup of moong dal = 200g, 1 cup of gram flour = 90g).
3. **Piece-to-Weight Mapping:** Count-based units for staple vegetables (potatoes, onions, tomatoes) are mapped to average weights (`PIECE_GRAMS`) to produce a coherent, unified shopping list.

---

### **Q7: What caching mechanism is implemented, and what are the performance gains?**
**Answer:**  
ThaliPlanner utilizes an in-memory LRU cache (`_RAG_CACHE`, max size 256) keyed by `(question.lower(), top_k)`.
- **Cache Miss (Fresh Query):** Executes hybrid parsing or vector retrieval ($\approx 15-30\text{ ms}$).
- **Cache Hit (Repeated Query):** Bypasses all disk, DB, and embedding operations, returning the structured response in **$\approx 0.18\text{ ms}$** ($\approx 100\times$ faster) with zero token consumption.

---

### **Q8: How do you ensure reproducibility and test quality across CI/CD?**
**Answer:**  
Every commit and pull request triggers a GitHub Actions workflow (`.github/workflows/ci.yml`) running on Python 3.11 with:
1. **Linting & Formatting:** `ruff check .` ensuring zero code smell, clean imports, and style consistency.
2. **Automated Test Suite:** `pytest tests/test_day11.py` executing **14 comprehensive unit tests** covering health endpoints, database loading, search accuracy, LLM abstention, grocery scaling, unit conversions, numerical filtering, prompt injection, and structured recipe formatting.
3. **Container Build Verification:** Verifying `docker build` succeeds with CPU-optimized PyTorch.

---

### **Q9: How is the application deployed to production?**
**Answer:**  
- **Containerization (`Dockerfile` & `docker-compose.yml`):** Uses a lightweight `python:3.12-slim` base image with CPU-only wheels for PyTorch to avoid unnecessary 2.5GB CUDA dependencies, keeping the image small and build times fast.
- **Render Deployment (`render.yaml`):** Two web services—the FastAPI backend serving public `/health`, `/docs`, and `/ask` endpoints, and the Streamlit frontend UI.
- **Hugging Face Spaces:** Streamlit Space configuration for open-access community demos.

---

### **Q10: If the dataset expanded from 20 to 100,000 recipes, what architectural changes would you make?**
**Answer:**  
1. **Distributed Vector Database:** Transition from local persistent ChromaDB to a managed, distributed vector database like **Qdrant** or **Pinecone** with HNSW indexing and metadata payload filtering.
2. **Distributed Caching:** Replace in-memory dictionary caching with **Redis** featuring TTL expiration and cluster replication.
3. **Asynchronous Task Queue:** Offload heavy PDF/HTML scraping and embedding regeneration to background workers via **Celery** or **RabbitMQ**.
4. **Quantized Embedding Models:** Deploy quantized ONNX or TensorRT models on specialized inference endpoints to maintain sub-50ms vector lookups.
