"""
ThaliPlanner — Streamlit Chat UI  (Day 10 / Checkpoint-2)

Features
--------
1. Chat interface  → calls /ask (RAG) or /agent endpoints; shows numbered citations
2. Thumbs 👍 / 👎 feedback → appended to ui/feedback.jsonl
3. Signature: 7-day Thali Grid (Mon-Sun × Breakfast/Lunch/Dinner)
   • Veg 🟢 / Vegan 🌱 / Contains-Paneer 🧀 chips
   • ⚠️ repeat-warning when the same DAL appears > 2 times in the week

Run:   streamlit run ui/app.py
       (FastAPI server optional — app falls back to direct RAG if /ask is offline)
"""

import sys
import os
import json
import datetime
import pathlib
import collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ThaliPlanner 🍛",
    page_icon="🍛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── constants ─────────────────────────────────────────────────────────────────
WORKSPACE = pathlib.Path(__file__).parent.parent
FEEDBACK_FILE = pathlib.Path(__file__).parent / "feedback.jsonl"
API_BASE = "http://localhost:8000"

DAYS   = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MEALS  = ["Breakfast", "Lunch", "Dinner"]

# Paneer dishes (by ID in records.json — 1-indexed)
PANEER_IDS = {12, 13}   # Matar Paneer, Paneer Butter Masala

NON_VEGAN = {"ghee", "butter", "cream", "milk", "curd", "paneer", "yogurt", "khoya"}

DAL_TYPE = "Dal"  # region_or_type value


# ── load recipe records ───────────────────────────────────────────────────────
@st.cache_data
def load_records():
    records_path = WORKSPACE / "data" / "records.json"
    if records_path.exists():
        with open(records_path, encoding="utf-8") as f:
            return json.load(f)
    return []


def classify(record):
    """Return (is_veg, is_vegan, has_paneer) for a recipe record."""
    rid  = record.get("id", 0)
    ingr = [i.lower() for i in record.get("ingredients", [])]
    has_paneer = rid in PANEER_IDS or any("paneer" in i for i in ingr)
    is_veg     = True   # all 20 recipes are vegetarian
    is_vegan   = not any(nv in " ".join(ingr) for nv in NON_VEGAN)
    return is_veg, is_vegan, has_paneer


def chips(record):
    """Return HTML chip string for a recipe."""
    is_veg, is_vegan, has_paneer = classify(record)
    parts = []
    if is_vegan:
        parts.append('<span style="background:#2d6a2d;color:#fff;padding:1px 7px;border-radius:12px;font-size:0.75rem">🌱 Vegan</span>')
    elif is_veg:
        parts.append('<span style="background:#3a7d44;color:#fff;padding:1px 7px;border-radius:12px;font-size:0.75rem">🟢 Veg</span>')
    if has_paneer:
        parts.append('<span style="background:#c97d4e;color:#fff;padding:1px 7px;border-radius:12px;font-size:0.75rem">🧀 Paneer</span>')
    return " ".join(parts)


# ── feedback helpers ──────────────────────────────────────────────────────────
def save_feedback(question, answer, rating):
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "question":  question,
        "answer":    answer[:200],
        "rating":    rating,          # "up" or "down"
    }
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ── RAG answer (direct, no server needed) ────────────────────────────────────
@st.cache_resource
def get_rag():
    """Try to import the RAG module directly (offline fallback)."""
    try:
        from app.rag import answer_question
        return answer_question
    except Exception:
        return None


def ask_question(question: str, use_agent: bool = False):
    """
    Call /ask (or /agent) endpoint; fall back to direct RAG.
    Returns dict: {answer, citations, abstained}
    """
    import urllib.request
    import urllib.error
    endpoint = f"{API_BASE}/agent" if use_agent else f"{API_BASE}/ask"
    payload   = json.dumps({"question": question}).encode()
    headers   = {"Content-Type": "application/json"}
    try:
        req  = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        pass  # fall through to direct RAG

    rag_fn = get_rag()
    if rag_fn:
        try:
            return rag_fn(question)
        except Exception as e:
            return {"answer": f"⚠️ RAG error: {e}", "citations": [], "abstained": True}

    return {
        "answer":    "⚠️ FastAPI server is offline and direct RAG is unavailable. "
                     "Please run `uvicorn app.main:app --reload` and refresh.",
        "citations": [],
        "abstained": True,
    }


# ── session state init ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []          # list of {role, content, citations, msg_id}

if "grid" not in st.session_state:
    # grid[day_idx][meal_idx] = recipe_id or 0 (none)
    st.session_state.grid = [[0] * len(MEALS) for _ in range(len(DAYS))]

if "mode" not in st.session_state:
    st.session_state.mode = "Chat 💬"

if "msg_counter" not in st.session_state:
    st.session_state.msg_counter = 0


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.image("https://em-content.zobj.net/source/twitter/376/shallow-pan-of-food_1f958.png", width=64)
    st.title("ThaliPlanner 🍛")
    st.caption("Your AI-powered Indian Meal Companion")
    st.divider()

    st.session_state.mode = st.radio(
        "🧭 Mode",
        ["Chat 💬", "Thali Grid 🗓️"],
        index=["Chat 💬", "Thali Grid 🗓️"].index(st.session_state.mode),
    )
    st.divider()

    with st.expander("ℹ️ How to use"):
        st.markdown(
            """
**Chat:**
- Type any question about Indian recipes, nutrition, or cooking.
- 👍 / 👎 to rate each answer.
- Toggle **Agent mode** for multi-step reasoning.

**Thali Grid:**
- Build your 7-day meal plan.
- Pick dishes for each slot (Mon–Sun × Breakfast/Lunch/Dinner).
- Watch for 🌱 Vegan, 🟢 Veg, 🧀 Paneer chips.
- ⚠️ warns you when a *dal* repeats > 2× in the week.
            """
        )

    st.divider()
    st.markdown(f"📡 API: [`localhost:8000`]({API_BASE}/docs)")
    st.caption("Run: `uvicorn app.main:app --reload`")


# ══════════════════════════════════════════════════════════════════════════════
# CHAT TAB
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.mode == "Chat 💬":
    st.header("ThaliPlanner Chat 💬")
    st.caption("Ask anything about Indian recipes · RAG-powered · Citations included")

    agent_mode = st.toggle("🤖 Agent mode (multi-step reasoning)", value=False)

    # ── render chat history ───────────────────────────────────────────────────
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            if msg["role"] == "assistant":
                citations = msg.get("citations", [])
                if citations:
                    with st.expander(f"📚 {len(citations)} citation(s)"):
                        for i, c in enumerate(citations, 1):
                            source = c.get("source", c.get("url", "unknown"))
                            text   = c.get("text", c.get("chunk", ""))
                            st.markdown(
                                f"**[{i}]** `{source}`  \n"
                                f"> {text[:300]}{'…' if len(text) > 300 else ''}"
                            )

                # feedback buttons
                mid = msg.get("msg_id", "")
                col1, col2, *_ = st.columns([1, 1, 8])
                with col1:
                    if st.button("👍", key=f"up_{mid}", help="Good answer"):
                        save_feedback(
                            msg.get("question", ""),
                            msg["content"],
                            "up",
                        )
                        st.toast("Thanks for the feedback! 🎉", icon="✅")
                with col2:
                    if st.button("👎", key=f"dn_{mid}", help="Bad answer"):
                        save_feedback(
                            msg.get("question", ""),
                            msg["content"],
                            "down",
                        )
                        st.toast("Noted — we'll improve! 🙏", icon="⚠️")

    # ── chat input ────────────────────────────────────────────────────────────
    if prompt := st.chat_input("Ask about a recipe, nutrition, regional dish…"):
        # user bubble
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # assistant bubble
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                result = ask_question(prompt, use_agent=agent_mode)

            answer    = result.get("answer", "")
            citations = result.get("citations", [])
            abstained = result.get("abstained", False)

            if abstained and not answer.startswith("⚠️"):
                answer = "🙅 I couldn't find enough information to answer confidently.\n\n" + answer

            st.markdown(answer)

            if citations:
                with st.expander(f"📚 {len(citations)} citation(s)"):
                    for i, c in enumerate(citations, 1):
                        source = c.get("source", c.get("url", "unknown"))
                        text   = c.get("text", c.get("chunk", ""))
                        st.markdown(
                            f"**[{i}]** `{source}`  \n"
                            f"> {text[:300]}{'…' if len(text) > 300 else ''}"
                        )

            # feedback row
            st.session_state.msg_counter += 1
            mid = st.session_state.msg_counter
            col1, col2, *_ = st.columns([1, 1, 8])
            with col1:
                if st.button("👍", key=f"up_new_{mid}"):
                    save_feedback(prompt, answer, "up")
                    st.toast("Thanks! 🎉", icon="✅")
            with col2:
                if st.button("👎", key=f"dn_new_{mid}"):
                    save_feedback(prompt, answer, "down")
                    st.toast("Noted 🙏", icon="⚠️")

        st.session_state.messages.append({
            "role":      "assistant",
            "content":   answer,
            "citations": citations,
            "question":  prompt,
            "msg_id":    mid,
        })


# ══════════════════════════════════════════════════════════════════════════════
# THALI GRID TAB  — Signature Feature
# ══════════════════════════════════════════════════════════════════════════════
else:
    records = load_records()
    # Build lookup maps
    id_to_rec  = {r["id"]: r for r in records}
    dish_names = ["— none —"] + [r["dish_name"] for r in records]
    name_to_id = {r["dish_name"]: r["id"] for r in records}

    st.header("🗓️ 7-Day Thali Grid")
    st.caption(
        "Plan your week · Pick dishes · "
        "🌱 Vegan | 🟢 Veg | 🧀 Paneer · "
        "⚠️ alerts when a dal repeats > 2× in the week"
    )

    # ── clear grid button ─────────────────────────────────────────────────────
    if st.button("🗑️ Clear Grid", type="secondary"):
        st.session_state.grid = [[0] * len(MEALS) for _ in range(len(DAYS))]
        st.rerun()

    st.divider()

    # ── grid header ───────────────────────────────────────────────────────────
    header_cols = st.columns([1] + [2] * len(DAYS))
    header_cols[0].markdown("**Meal**")
    for i, day in enumerate(DAYS):
        header_cols[i + 1].markdown(f"**{day[:3]}**")

    st.divider()

    # ── grid rows ─────────────────────────────────────────────────────────────
    for mi, meal in enumerate(MEALS):
        row_cols = st.columns([1] + [2] * len(DAYS))
        row_cols[0].markdown(f"**{meal}**")

        for di, day in enumerate(DAYS):
            with row_cols[di + 1]:
                current_id   = st.session_state.grid[di][mi]
                current_name = id_to_rec[current_id]["dish_name"] if current_id else "— none —"

                selected = st.selectbox(
                    label=f"{day} {meal}",
                    options=dish_names,
                    index=dish_names.index(current_name),
                    key=f"grid_{di}_{mi}",
                    label_visibility="collapsed",
                )

                # update session state
                new_id = name_to_id.get(selected, 0)
                st.session_state.grid[di][mi] = new_id

                # show chips
                if new_id:
                    rec = id_to_rec[new_id]
                    chip_html = chips(rec)
                    if chip_html:
                        st.markdown(chip_html, unsafe_allow_html=True)

    st.divider()

    # ── dal repeat warning ────────────────────────────────────────────────────
    dal_count: dict[str, int] = collections.Counter()
    for di in range(len(DAYS)):
        for mi in range(len(MEALS)):
            rid = st.session_state.grid[di][mi]
            if rid and id_to_rec[rid].get("region_or_type") == DAL_TYPE:
                dal_count[id_to_rec[rid]["dish_name"]] += 1

    warnings = [(name, cnt) for name, cnt in dal_count.items() if cnt > 2]
    if warnings:
        st.markdown("### ⚠️ Dal Repeat Warnings")
        for name, cnt in warnings:
            st.warning(
                f"**{name}** appears **{cnt} times** this week — "
                "try to vary your dals for better nutrition!",
                icon="⚠️",
            )
    else:
        if any(dal_count.values()):
            st.success("✅ Dal variety looks good this week!", icon="✅")

    # ── weekly summary ────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📊 Weekly Summary")

    total_filled  = sum(1 for di in range(len(DAYS)) for mi in range(len(MEALS)) if st.session_state.grid[di][mi])
    total_slots   = len(DAYS) * len(MEALS)
    vegan_count   = sum(
        1 for di in range(len(DAYS)) for mi in range(len(MEALS))
        if st.session_state.grid[di][mi] and classify(id_to_rec[st.session_state.grid[di][mi]])[1]
    )
    paneer_count  = sum(
        1 for di in range(len(DAYS)) for mi in range(len(MEALS))
        if st.session_state.grid[di][mi] and classify(id_to_rec[st.session_state.grid[di][mi]])[2]
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Slots Filled",   f"{total_filled}/{total_slots}")
    c2.metric("🌱 Vegan Meals", vegan_count)
    c3.metric("🧀 Paneer Meals", paneer_count)
    c4.metric("🫘 Dal Meals",    sum(dal_count.values()))
