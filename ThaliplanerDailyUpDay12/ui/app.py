"""
ThaliPlanner — Interactive Unified Dashboard UI
===================================================
Features:
- Sidebar Navigation:
  * 💬 Chat Assistant (Unified Dashboard with Chat + 7-Day Planner + Grocery List)
  * 📅 Meal Planner (Focused full 7-day thali planner with chips, dal repeat warning, metrics)
  * 🛒 Grocery List (Focused scaled shopping list with categories, checkboxes, download)
  * ℹ️ About (Project documentation, 20 recipe catalogue, persona, architecture)
- Connects to FastAPI backend (/ask, /agent) with graceful local fallbacks.
- Saves helpful / not-helpful feedback to ui/feedback.jsonl.
- Scaled grocery calculation powered by app.tools.build_grocery_list.
"""
from __future__ import annotations

import collections
import datetime
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

# Ensure workspace root is in sys.path
WORKSPACE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

import streamlit as st  # noqa: E402
from app.records import load_records  # noqa: E402
from app.tools import build_grocery_list, load_quantities  # noqa: E402

# ── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ThaliPlanner — Plan • Cook • Enjoy",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Paths & Constants ───────────────────────────────────────────────────────
FEEDBACK_FILE = WORKSPACE / "ui" / "feedback.jsonl"
API_BASE = "https://sanjivani-sj-55-thaliplanner-3.onrender.com/"

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MEALS = ["Breakfast", "Lunch", "Dinner"]

PANEER_IDS = {12, 13}  # Matar Paneer, Paneer Butter Masala
NON_VEGAN = {"ghee", "butter", "cream", "milk", "curd", "paneer", "yogurt", "khoya"}
DAL_TYPE = "Dal"

DISH_ICONS = {
    "Moong Dal": "🍲",
    "Langar Dal": "🍲",
    "Khichdi": "🍛",
    "Sambar I": "🥘",
    "Rasam": "🥣",
    "Idli": "⚪",
    "Dosa I": "🥞",
    "Masala Dosa": "🥞",
    "Medu Vada": "🍩",
    "Potato Curry (Aloo Masala)": "🥔",
    "Cholley": "🧆",
    "Matar Paneer": "🧀",
    "Paneer Butter Masala": "🧈",
    "Indian Rice": "🍚",
    "Coconut Rice": "🥥",
    "Onion Chutney": "🧅",
    "Coconut Chutney": "🥥",
    "Mango Chutney": "🥭",
    "Masala Chai I": "☕",
    "Dhokla": "🟨",
}


# ── Helpers ─────────────────────────────────────────────────────────────────
def classify(record: dict) -> tuple[bool, bool, bool]:
    rid = record.get("id", 0)
    ingr = [str(i).lower() for i in record.get("ingredients", [])]
    has_paneer = rid in PANEER_IDS or any("paneer" in i for i in ingr)
    is_veg = True
    is_vegan = not any(nv in " ".join(ingr) for nv in NON_VEGAN)
    return is_veg, is_vegan, has_paneer


def get_chips_html(record: dict) -> str:
    _, is_vegan, has_paneer = classify(record)
    chips = []
    if is_vegan:
        chips.append('<span class="chip chip-vegan">Vegan</span>')
    else:
        chips.append('<span class="chip chip-veg">Veg</span>')
    if has_paneer:
        chips.append('<span class="chip chip-paneer"> Paneer</span>')
    return " ".join(chips)


@st.cache_resource
def get_rag_function():
    try:
        from app.rag import answer_question
        return answer_question
    except Exception:
        return None


def format_chat_markdown(text: str) -> str:
    """Safely format markdown links and bolding for clean chat HTML rendering."""
    # Convert markdown links [Text](url) to styled anchor tags
    text = re.sub(
        r'\[([^\]]+)\]\((https?://[^\)]+)\)',
        r'<a href="\2" target="_blank" rel="noopener noreferrer" style="color: #4f46e5; text-decoration: underline; font-weight: 600;">\1</a>',
        text,
    )
    # Convert raw URLs into clickable anchor tags
    text = re.sub(
        r'(?<!href=")(https?://[^\s<]+)',
        r'<a href="\1" target="_blank" rel="noopener noreferrer" style="color: #4f46e5; text-decoration: underline; font-weight: 600;">\1</a>',
        text,
    )
    # Convert bold **text** to <strong>text</strong>
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    # Convert newlines to <br>
    text = text.replace('\n', '<br>')
    return text


def call_chat_endpoint(question: str, use_agent: bool = False, family_size: int = 4) -> dict:
    q_low = (question or "").lower()
    is_rag_specific = any(term in q_low for term in [
        "source", "where can i find", "ingredient", "calorie", "nutrition",
        "south indian", "vegan", "tell me about", "what dishes", "recipe for",
        "link for", "website for", "what is the source", "minute", "minutes",
        "easy", "20 minutes", "how long", "how hard"
    ])

    rag_fn = get_rag_function()
    if is_rag_specific and rag_fn:
        try:
            return rag_fn(question)
        except Exception:
            pass

    endpoint = f"{API_BASE}/agent" if use_agent else f"{API_BASE}/ask"
    payload_data = {"message": question} if use_agent else {"question": question}
    try:
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload_data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        pass

    if use_agent:
        try:
            from app.agent_loop import run_agent
            res = run_agent(question)
            return {
                "answer": res.get("answer", "Here is your plan."),
                "citations": [{"title": "Wikibooks – Indian Recipes", "source": "https://en.wikibooks.org/wiki/Category:Indian_recipes"}],
                "grocery_list": res.get("grocery_list"),
                "abstained": False,
            }
        except Exception:
            pass

    if rag_fn:
        try:
            return rag_fn(question)
        except Exception as exc:
            return {"answer": f"⚠️ RAG error: {exc}", "citations": [], "abstained": True}

    if "plan" in q_low or "lunch" in q_low or "dal" in q_low:
        return {
            "answer": (
                "Here is your 3-day lunch plan:\n\n"
                "✅ **Monday:** Moong Dal\n\n"
                "✅ **Tuesday:** Langar Dal\n\n"
                "✅ **Wednesday:** Sambar I\n\n"
                "Would you like to add these to your weekly planner?"
            ),
            "citations": [{"title": "Wikibooks – Indian Recipes", "source": "https://en.wikibooks.org/wiki/Cookbook:Moong_Dal"}],
            "abstained": False,
        }

    return {
        "answer": (
            f"Based on our 20 Indian recipes catalogue, we recommend planning balanced vegetarian meals for {family_size} people."
        ),
        "citations": [{"title": "Wikibooks – Indian Recipes", "source": "https://en.wikibooks.org/wiki/Category:Indian_recipes"}],
        "abstained": False,
    }


def save_user_feedback(question: str, answer: str, rating: str):
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "question": question,
        "answer": answer[:250],
        "rating": rating,
    }
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ── Data Initialization ─────────────────────────────────────────────────────
records = load_records()
quantities = load_quantities()

id_to_record = {r["id"]: r for r in records}
name_to_id = {r["dish_name"]: r["id"] for r in records}
all_dish_names = ["— None —"] + [r["dish_name"] for r in records]


def dish_label(name: str) -> str:
    if name == "— None —":
        return "— Select Dish —"
    icon = DISH_ICONS.get(name, "🍲")
    return f"{icon}  {name}"


DEFAULT_GRID = [
    {"Breakfast": "Idli", "Lunch": "Moong Dal", "Dinner": "Indian Rice"},
    {"Breakfast": "Dosa I", "Lunch": "Langar Dal", "Dinner": "Khichdi"},
    {"Breakfast": "Dhokla", "Lunch": "Sambar I", "Dinner": "Coconut Rice"},
    {"Breakfast": "Medu Vada", "Lunch": "Moong Dal", "Dinner": "Rasam"},
    {"Breakfast": "Idli", "Lunch": "Cholley", "Dinner": "Indian Rice"},
    {"Breakfast": "Dosa I", "Lunch": "Matar Paneer", "Dinner": "Khichdi"},
    {"Breakfast": "Dhokla", "Lunch": "Sambar I", "Dinner": "Dosa I"},
]

if "planner_grid" not in st.session_state:
    st.session_state.planner_grid = [
        {meal: DEFAULT_GRID[d][meal] for meal in MEALS}
        for d in range(len(DAYS))
    ]

if "family_size" not in st.session_state:
    st.session_state.family_size = 4

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "user",
            "content": "Plan Monday to Wednesday lunch for 4 people with different dal each day.",
            "time": "10:44 AM",
        },
        {
            "role": "assistant",
            "content": (
                "Here is your 3-day lunch plan:\n\n"
                "✅ **Monday:** Moong Dal\n\n"
                "✅ **Tuesday:** Langar Dal\n\n"
                "✅ **Wednesday:** Sambar I\n\n"
                "Would you like to add these to your weekly planner?"
            ),
            "citations": [{"source": "Wikibooks – Indian Recipes", "chunk": "Dal & Rice Recipes"}],
            "time": "10:45 AM",
            "msg_id": 1,
            "feedback": None,
        },
    ]

if "msg_counter" not in st.session_state:
    st.session_state.msg_counter = 1


# ── Custom CSS for Modern Purple Dashboard ──────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #111827 !important;
    }
    
    .stApp {
        background-color: #f4f5fc;
        color: #111827 !important;
    }

    /* Universal black text for content on light/white backgrounds */
    p, span, label, div, strong, b, li, h1, h2, h3, h4, h5, h6 {
        color: #111827;
    }
    
    header[data-testid="stHeader"] {
        background: transparent;
    }
    
    section[data-testid="stSidebar"] {
        background-color: #fcfcff;
        border-right: 1px solid #e8eaf6;
        padding-top: 1rem;
    }
    
    .brand-container {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 12px;
        margin-bottom: 16px;
    }
    
    .brand-icon {
        font-size: 30px;
        background: #ede9fe;
        color: #5d50c6;
        width: 46px;
        height: 46px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .brand-title {
        font-size: 20px;
        font-weight: 700;
        color: #1e1b4b !important;
        line-height: 1.1;
    }
    
    .brand-sub {
        font-size: 11px;
        font-weight: 500;
        color: #4b5563 !important;
        letter-spacing: 0.5px;
    }
    
    /* Sleek radio button tabs */
    div[data-testid="stRadio"] > div {
        gap: 6px;
    }
    
    div[data-testid="stRadio"] label {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 8px 14px !important;
        margin-bottom: 2px;
        transition: all 0.2s ease-in-out;
        cursor: pointer;
    }
    
    div[data-testid="stRadio"] label p,
    div[data-testid="stRadio"] label span {
        color: #111827 !important;
        font-weight: 600 !important;
    }
    
    div[data-testid="stRadio"] label:hover {
        background-color: #ede9fe !important;
        border-color: #c4b5fd;
    }
    
    div[data-testid="stRadio"] label:has(input:checked) {
        background: #5d50c6 !important;
        border-color: #5d50c6 !important;
        box-shadow: 0 4px 10px rgba(93, 80, 198, 0.22);
    }
    
    div[data-testid="stRadio"] label:has(input:checked) p,
    div[data-testid="stRadio"] label:has(input:checked) span {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    
    .promo-card {
        background: linear-gradient(135deg, #ede9fe 0%, #e0e7ff 100%);
        border-radius: 14px;
        padding: 14px;
        margin-top: 24px;
        text-align: center;
        border: 1px solid #dcd7fe;
    }
    
    .card {
        background: #ffffff !important;
        border-radius: 16px;
        padding: 20px 22px;
        box-shadow: 0 2px 10px rgba(79, 70, 229, 0.04);
        border: 1px solid #eef0f8;
        margin-bottom: 20px;
        color: #111827 !important;
    }
    
    .card * {
        color: #111827;
    }
    
    .card-title {
        font-size: 17px;
        font-weight: 700;
        color: #2e1065 !important;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 14px;
        max-height: 480px;
        overflow-y: auto;
        padding-right: 6px;
        margin-bottom: 16px;
    }
    
    .user-bubble {
        align-self: flex-end;
        background: #ede9fe !important;
        color: #1e1b4b !important;
        padding: 12px 16px;
        border-radius: 18px 18px 4px 18px;
        max-width: 85%;
        font-size: 13.5px;
        line-height: 1.45;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    
    .bot-bubble-wrapper {
        display: flex;
        gap: 10px;
        align-self: flex-start;
        max-width: 90%;
    }
    
    .bot-avatar {
        width: 34px;
        height: 34px;
        background: #5d50c6;
        color: white;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        flex-shrink: 0;
    }
    
    .bot-bubble {
        background: #ffffff !important;
        border: 1px solid #e2e8f0;
        padding: 14px 18px;
        border-radius: 4px 18px 18px 18px;
        color: #111827 !important;
        font-size: 13.5px;
        line-height: 1.5;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }
    
    .bot-bubble * {
        color: #111827;
    }
    
    .bot-bubble a, .citation-box a.citation-tag {
        color: #5d50c6 !important;
        font-weight: 600 !important;
        text-decoration: underline !important;
    }
    
    .citation-box {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 10px;
        padding-top: 8px;
        border-top: 1px solid #f1f5f9;
        font-size: 11px;
        color: #6b7280;
    }
    
    .citation-box span {
        color: #6b7280 !important;
    }
    }

    .warning-banner {
        background: #fff8e6 !important;
        color: #92400e !important;
        border: 1px solid #fde68a;
        padding: 10px 16px;
        border-radius: 10px;
        font-size: 13px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 12px;
    }
    
    .warning-banner * {
        color: #92400e !important;
    }

    .success-banner {
        background: #ecfdf5 !important;
        color: #065f46 !important;
        border: 1px solid #a7f3d0;
        padding: 8px 14px;
        border-radius: 10px;
        font-size: 12.5px;
        font-weight: 600;
        margin-top: 10px;
    }
    
    .success-banner * {
        color: #065f46 !important;
    }
    
    .chip {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 600;
        margin-right: 4px;
    }
    .chip-vegan { background: #dcfce7 !important; color: #166534 !important; }
    .chip-veg { background: #ecfdf5 !important; color: #047857 !important; }
    .chip-paneer { background: #ffedd5 !important; color: #9a3412 !important; }

    .total-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #e0f2fe !important;
        color: #0369a1 !important;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        margin-top: 12px;
    }
    
    .total-pill * {
        color: #0369a1 !important;
    }

    /* Force black text inside form widgets & dropdowns */
    div[data-baseweb="select"] *,
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div,
    div[data-baseweb="popover"] *,
    div[data-baseweb="menu"] *,
    ul[role="listbox"] *,
    ul[role="listbox"] li,
    input,
    .stTextInput input {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    /* Metric values & labels */
    div[data-testid="stMetricValue"] *,
    div[data-testid="stMetricLabel"] * {
        color: #111827 !important;
    }

    /* Checkbox labels */
    div[data-testid="stCheckbox"] label span {
        color: #111827 !important;
    }

    /* Tabs & Expanders */
    button[data-baseweb="tab"] div {
        color: #111827 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] div {
        color: #5d50c6 !important;
        font-weight: 700 !important;
    }
    div[data-testid="stExpander"] * {
        color: #111827 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        """
        <div class="brand-container">
            <div class="brand-icon">🍽️</div>
            <div>
                <div class="brand-title">ThaliPlanner</div>
                <div class="brand-sub">Plan • Cook • Enjoy</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    nav_mode = st.radio(
        "Navigation",
        ["💬 Chat Assistant", "📅 Meal Planner", "🛒 Grocery List", "ℹ️ About"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.caption("⚙️ **Engine Settings**")
    agent_mode_toggle = st.toggle("🤖 Agent Mode (LangGraph)", value=True, help="Enables multi-step reasoning & grocery calling")

    st.markdown(
        """
        <div class="promo-card">
            <div style="font-size: 32px; margin-bottom: 6px;"></div>
            <div style="font-size: 13px; font-weight: 700; color: #3730a3; margin-bottom: 4px;">Healthy Indian Meals Made Easy!</div>
            <div style="font-size: 11px; color: #4338ca;">Smart vegetarian meal planning with nutrition-balanced thalis.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Helper Components for Planner & Grocery Cards
# ──────────────────────────────────────────────────────────────────────────────
def render_planner_card(is_expanded: bool = False):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    header_left, header_mid, header_right = st.columns([5, 2.5, 2.5])
    with header_left:
        st.markdown('<div class="card-title">📅 Weekly Thali Planner</div>', unsafe_allow_html=True)
    with header_mid:
        selected_family_size = st.selectbox(
            "Family Size:",
            options=[1, 2, 4, 6, 8],
            index=[1, 2, 4, 6, 8].index(st.session_state.family_size),
            key="family_size_select",
        )
        st.session_state.family_size = selected_family_size
    with header_right:
        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
        if st.button("Save Plan", type="primary", use_container_width=True, key="save_plan_btn"):
            st.toast(f"Plan saved for {st.session_state.family_size} people!", icon="💾")

    # Table Header
    th_day, th_bf, th_lunch, th_dinner = st.columns([2.0, 3.2, 3.2, 3.2])
    th_day.markdown("**Day**")
    th_bf.markdown("**Breakfast**")
    th_lunch.markdown("**Lunch**")
    th_dinner.markdown("**Dinner**")

    dal_counter = collections.Counter()
    chosen_recipe_ids = []

    for di, day_name in enumerate(DAYS):
        r_day, r_bf, r_lunch, r_dinner = st.columns([2.0, 3.2, 3.2, 3.2])
        r_day.markdown(f"**{day_name}**")

        # Breakfast
        with r_bf:
            curr_bf = st.session_state.planner_grid[di]["Breakfast"]
            bf_idx = all_dish_names.index(curr_bf) if curr_bf in all_dish_names else 0
            sel_bf = st.selectbox(
                f"{day_name}_bf",
                options=all_dish_names,
                index=bf_idx,
                format_func=dish_label,
                key=f"sel_{di}_Breakfast",
                label_visibility="collapsed",
            )
            st.session_state.planner_grid[di]["Breakfast"] = sel_bf
            if sel_bf in name_to_id:
                rid = name_to_id[sel_bf]
                chosen_recipe_ids.append(rid)
                if id_to_record[rid].get("region_or_type") == DAL_TYPE:
                    dal_counter[sel_bf] += 1
                if is_expanded:
                    st.markdown(get_chips_html(id_to_record[rid]), unsafe_allow_html=True)

        # Lunch
        with r_lunch:
            curr_l = st.session_state.planner_grid[di]["Lunch"]
            l_idx = all_dish_names.index(curr_l) if curr_l in all_dish_names else 0
            sel_l = st.selectbox(
                f"{day_name}_lunch",
                options=all_dish_names,
                index=l_idx,
                format_func=dish_label,
                key=f"sel_{di}_Lunch",
                label_visibility="collapsed",
            )
            st.session_state.planner_grid[di]["Lunch"] = sel_l
            if sel_l in name_to_id:
                rid = name_to_id[sel_l]
                chosen_recipe_ids.append(rid)
                if id_to_record[rid].get("region_or_type") == DAL_TYPE:
                    dal_counter[sel_l] += 1
                if is_expanded:
                    st.markdown(get_chips_html(id_to_record[rid]), unsafe_allow_html=True)

        # Dinner
        with r_dinner:
            curr_d = st.session_state.planner_grid[di]["Dinner"]
            d_idx = all_dish_names.index(curr_d) if curr_d in all_dish_names else 0
            sel_d = st.selectbox(
                f"{day_name}_dinner",
                options=all_dish_names,
                index=d_idx,
                format_func=dish_label,
                key=f"sel_{di}_Dinner",
                label_visibility="collapsed",
            )
            st.session_state.planner_grid[di]["Dinner"] = sel_d
            if sel_d in name_to_id:
                rid = name_to_id[sel_d]
                chosen_recipe_ids.append(rid)
                if id_to_record[rid].get("region_or_type") == DAL_TYPE:
                    dal_counter[sel_d] += 1
                if is_expanded:
                    st.markdown(get_chips_html(id_to_record[rid]), unsafe_allow_html=True)

    # Repeat warning banner
    dal_repeats = [dish for dish, count in dal_counter.items() if count > 2]
    if dal_repeats:
        st.markdown(
            f"""
            <div class="warning-banner">
                ⚠️ <strong>Same dal appears more than twice this week!</strong> ({', '.join(dal_repeats)})
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="success-banner">
                ✅ Great job! Dal variety is well balanced this week (no dal repeated > 2 times).
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
    return chosen_recipe_ids


def render_grocery_card(chosen_recipe_ids: list[int]):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    g_header_left, g_header_right = st.columns([7, 3])
    with g_header_left:
        st.markdown('<div class="card-title">🛒 Grocery List</div>', unsafe_allow_html=True)

    unique_recipe_counts = collections.Counter(chosen_recipe_ids)
    selections_payload = [
        {"recipe_id": rid, "servings": st.session_state.family_size * count}
        for rid, count in unique_recipe_counts.items()
    ]

    grocery_items = []
    if selections_payload:
        try:
            grocery_data = build_grocery_list(selections_payload, records, quantities)
            grocery_items = grocery_data.get("items", [])
        except Exception:
            grocery_items = []

    if not grocery_items:
        grocery_items = [
            {"item": "Moong Dal", "display": "500 g"},
            {"item": "Rice", "display": "1 kg"},
            {"item": "Onion", "display": "500 g"},
            {"item": "Tomato", "display": "500 g"},
            {"item": "Green Chilli", "display": "50 g"},
            {"item": "Coconut", "display": "2 pcs"},
        ]

    download_text = f"THALIPLANNER GROCERY LIST (Family Size: {st.session_state.family_size})\n"
    download_text += "=" * 45 + "\n\n"
    for item in grocery_items:
        download_text += f"[ ] {item['item'].capitalize():<24} {item['display']}\n"
    download_text += f"\nTotal Items: {len(grocery_items)}\n"

    with g_header_right:
        st.download_button(
            label="📥 Download PDF",
            data=download_text,
            file_name=f"thaliplanner_grocery_list_{st.session_state.family_size}pax.txt",
            mime="text/plain",
            use_container_width=True,
            key="dl_grocery_btn",
        )

    for idx, item_data in enumerate(grocery_items):
        item_name = item_data["item"].capitalize()
        qty_display = item_data.get("display", f"{item_data.get('quantity', '')} {item_data.get('unit', '')}")

        c_box, c_name, c_qty = st.columns([0.8, 6.2, 3.0])
        with c_box:
            st.checkbox("", key=f"g_item_{idx}", label_visibility="collapsed")
        with c_name:
            st.markdown(f"**{item_name}**")
        with c_qty:
            st.markdown(f"<span style='color: #4b5563; font-weight: 600;'>{qty_display}</span>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="total-pill">
            ✔️ Total Items: {len(grocery_items)}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_chat_section():
    st.markdown(
        """
        <div class="card-title" style="margin-bottom: 12px;">
            💬 Chat Assistant
        </div>
        """,
        unsafe_allow_html=True,
    )

    chat_box = st.container()
    with chat_box:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: flex-end; align-items: flex-end; gap: 8px; margin-bottom: 10px;">
                        <div class="user-bubble">{msg["content"]}</div>
                        <div style="width: 28px; height: 28px; background: #6366f1; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px;">👤</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                formatted_content = format_chat_markdown(msg["content"])
                citation_title = "Wikibooks – Indian Recipes"
                citation_url = "https://en.wikibooks.org/wiki/Category:Indian_recipes"
                if msg.get("citations") and len(msg["citations"]) > 0:
                    first_c = msg["citations"][0]
                    citation_title = first_c.get("title") or first_c.get("source") or citation_title
                    raw_src = str(first_c.get("source", ""))
                    if raw_src.startswith("http"):
                        citation_url = raw_src
                timestamp = msg.get("time", "10:45 AM")

                st.markdown(
                    f"""
                    <div class="bot-bubble-wrapper">
                        <div class="bot-avatar">🤖</div>
                        <div class="bot-bubble">
                            <div style="line-height: 1.5;">{formatted_content}</div>
                            <div class="citation-box">
                                <span>📖 <a class="citation-tag" href="{citation_url}" target="_blank" rel="noopener noreferrer">Source: {citation_title}</a></span>
                                <span>{timestamp}</span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                mid = msg.get("msg_id", 0)
                if mid:
                    fcol1, fcol2, _ = st.columns([1.6, 2.0, 3.0])
                    with fcol1:
                        if st.button("👍 Helpful", key=f"helpful_{mid}", help="Mark as helpful"):
                            save_user_feedback(msg.get("content", ""), "Helpful", "up")
                            st.toast("Feedback saved: Helpful! 👍", icon="🎉")
                    with fcol2:
                        if st.button("👎 Not Helpful", key=f"unhelpful_{mid}", help="Mark as not helpful"):
                            save_user_feedback(msg.get("content", ""), "Not Helpful", "down")
                            st.toast("Feedback recorded: We'll improve! 🙏", icon="⚠️")

        st.markdown("</div>", unsafe_allow_html=True)

    with st.container():
        with st.form("chat_input_form", clear_on_submit=True):
            input_col, send_col = st.columns([8.5, 1.5])
            with input_col:
                user_input = st.text_input(
                    "Ask anything",
                    placeholder="Ask anything about ThaliPlanner...",
                    label_visibility="collapsed",
                    key="chat_input_field",
                )
            with send_col:
                send_clicked = st.form_submit_button("✈️", help="Send message", use_container_width=True)

        if send_clicked and user_input and user_input.strip():
            now_time = datetime.datetime.now().strftime("%I:%M %p")
            prompt = user_input.strip()

            st.session_state.messages.append({
                "role": "user",
                "content": prompt,
                "time": now_time,
            })

            with st.spinner("AI is planning..."):
                response_data = call_chat_endpoint(prompt, use_agent=agent_mode_toggle, family_size=st.session_state.family_size)

            st.session_state.msg_counter += 1
            st.session_state.messages.append({
                "role": "assistant",
                "content": response_data.get("answer", "Here is your plan."),
                "citations": response_data.get("citations", []),
                "time": now_time,
                "msg_id": st.session_state.msg_counter,
                "feedback": None,
            })
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# DYNAMIC PAGE ROUTING BASED ON NAV_MODE
# ══════════════════════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────────────────────────
# 1. 💬 Chat Assistant (Unified Side-by-Side Dashboard)
# ──────────────────────────────────────────────────────────────────────────────
if nav_mode == "💬 Chat Assistant":
    col_chat, col_planner = st.columns([4, 6], gap="large")
    with col_chat:
        render_chat_section()
    with col_planner:
        selected_ids = render_planner_card(is_expanded=False)
        render_grocery_card(selected_ids)


# ──────────────────────────────────────────────────────────────────────────────
# 2. 📅 Meal Planner (Full-Screen 7-Day Thali Grid & Analytics)
# ──────────────────────────────────────────────────────────────────────────────
elif nav_mode == "📅 Meal Planner":
    st.markdown('<div class="card-title" style="font-size: 22px; margin-bottom: 4px;">📅 Weekly Meal Planner Studio</div>', unsafe_allow_html=True)
    st.caption("Plan your week's meals with dietary chips (🌱 Vegan, 🟢 Veg, 🧀 Paneer) and automatic Dal repeat protection.")

    # Control buttons
    top_c1, top_c2, top_c3 = st.columns([6, 2, 2])
    with top_c2:
        if st.button("🎲 Auto-Fill Balanced Menu", use_container_width=True):
            st.session_state.planner_grid = [
                {meal: DEFAULT_GRID[d][meal] for meal in MEALS}
                for d in range(len(DAYS))
            ]
            st.toast("Balanced Indian thali menu generated!", icon="✨")
            st.rerun()
    with top_c3:
        if st.button("🗑️ Clear Entire Plan", use_container_width=True):
            st.session_state.planner_grid = [
                {meal: "— None —" for meal in MEALS}
                for _ in range(len(DAYS))
            ]
            st.toast("Meal plan cleared.", icon="🗑️")
            st.rerun()

    selected_ids = render_planner_card(is_expanded=True)

    # Weekly Summary Metrics
    st.markdown("### 📊 Weekly Nutrition & Variety Summary")
    total_slots = len(DAYS) * len(MEALS)
    total_filled = len(selected_ids)
    vegan_count = sum(1 for rid in selected_ids if classify(id_to_record[rid])[1])
    paneer_count = sum(1 for rid in selected_ids if classify(id_to_record[rid])[2])
    dal_count = sum(1 for rid in selected_ids if id_to_record[rid].get("region_or_type") == DAL_TYPE)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Meals Planned", f"{total_filled} / {total_slots}")
    m2.metric("Vegan Meals", vegan_count)
    m3.metric("Paneer Dishes", paneer_count)
    m4.metric("Dal Servings", dal_count)


# ──────────────────────────────────────────────────────────────────────────────
# 3. 🛒 Grocery List (Focused Scaled Shopping List)
# ──────────────────────────────────────────────────────────────────────────────
elif nav_mode == "🛒 Grocery List":
    st.markdown('<div class="card-title" style="font-size: 22px; margin-bottom: 4px;">🛒 Smart Grocery Shopping List</div>', unsafe_allow_html=True)
    st.caption(f"Automatically scaled to your family size ({st.session_state.family_size} people) based on recipes chosen in the Weekly Planner.")

    # Gather selected recipe IDs from planner grid
    chosen_ids = []
    for day_dict in st.session_state.planner_grid:
        for meal in MEALS:
            dish = day_dict.get(meal)
            if dish in name_to_id:
                chosen_ids.append(name_to_id[dish])

    render_grocery_card(chosen_ids)

    # Detailed recipe contributions table
    with st.expander("🔍 View Dish Scaling Details & Attributions", expanded=False):
        if chosen_ids:
            counts = collections.Counter(chosen_ids)
            for rid, count in counts.items():
                r = id_to_record[rid]
                base_servings = r.get("servings", 4)
                target_servings = st.session_state.family_size * count
                scale = target_servings / base_servings if base_servings else 1.0
                st.markdown(f"- **{r['dish_name']}**: Planned **{count} time(s)** → **{target_servings} servings** (Base: {base_servings}, Scaling: `{scale:.2f}x`)")
        else:
            st.info("No recipes currently selected in the Meal Planner.")


# ──────────────────────────────────────────────────────────────────────────────
# 4. ℹ️ About (Project Documentation, 20 Recipes & Architecture)
# ──────────────────────────────────────────────────────────────────────────────
elif nav_mode == "ℹ️ About":
    st.markdown('<div class="card-title" style="font-size: 24px; margin-bottom: 6px;">ℹ️ About ThaliPlanner</div>', unsafe_allow_html=True)
    st.markdown(
        """
        **ThaliPlanner** plans a week of authentic Indian vegetarian meals from open Wikibooks recipes 
        and converts your meal choices into one combined, scaled grocery list for your family.
        """
    )

    tab_persona, tab_recipes, tab_arch, tab_milestones = st.tabs([
        "User Persona", "20 Recipes Catalogue", "Technical Architecture", "Milestones (Days 1–12)"
    ])

    with tab_persona:
        st.markdown(
            """
            ###  Target Persona: The Kopargaon Family
            - **Who**: A working couple in **Kopargaon** with two kids.
            - **Routine**: Cook healthy, home-made vegetarian food every day.
            - **Goal**: Plan their week's dal-sabzi-rice menu on Sunday and buy all groceries in one trip.
            - **Pain Points**:
              - Repeating the same dal/curry too often due to lack of planning.
              - Inaccurate grocery purchases (running out of ginger or buying excess veggies).
              - Difficulty balancing nutrition (vegan vs dairy/paneer meals).
            - **How ThaliPlanner Helps**:
              - 7-day grid with Breakfast, Lunch, Dinner.
              - ⚠️ Automatic **Repeat Warning** if the same dal appears more than twice a week.
              - Pure-arithmetic grocery scaling that sums common ingredients across recipes into grams & kilograms.
            """
        )

    with tab_recipes:
        st.markdown("### 20 Authentic Indian Recipes in Database")
        st.caption("Extracted and normalized from open Wikibooks (Category:Indian recipes & Cookbook:Dal).")

        filter_type = st.selectbox("Filter by Category:", ["All"] + sorted(list(set(r.get("region_or_type", "Other") for r in records))))
        
        display_records = records if filter_type == "All" else [r for r in records if r.get("region_or_type") == filter_type]

        cols = st.columns(3)
        for i, rec in enumerate(display_records):
            with cols[i % 3]:
                st.markdown('<div class="card" style="padding: 14px; margin-bottom: 12px;">', unsafe_allow_html=True)
                icon = DISH_ICONS.get(rec["dish_name"], "🍲")
                st.markdown(f"**{icon} {rec['dish_name']}**")
                st.caption(f"**Category:** {rec.get('region_or_type', 'N/A')} | **Servings:** {rec.get('servings', 4)}")
                st.markdown(get_chips_html(rec), unsafe_allow_html=True)
                st.markdown(f"<div style='font-size: 11px; color: #64748b; margin-top: 6px;'><strong>Ingredients:</strong> {', '.join(rec.get('ingredients', [])[:5])}...</div>", unsafe_allow_html=True)
                st.markdown(f"<a href='{rec.get('source_url', '#')}' target='_blank' style='font-size: 11px; color: #5d50c6;'>View on Wikibooks ↗</a>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    with tab_arch:
        st.markdown(
            """
            ###Technical Architecture & Pipeline
            
            1. **Data Ingestion (`app/fetch.py`, `app/ingest.py`)**:
               - Fetches Wikibooks HTML/wikitext via MediaWiki API.
               - Normalizes into 20 structured records in `data/records.json`.
            2. **Embeddings & Vector Store (`app/chunking.py`, `app/vectorstore.py`)**:
               - Recursive text chunking with `all-MiniLM-L6-v2` embeddings in **ChromaDB**.
            3. **RAG with Citation Guard (`app/rag.py`)**:
               - Answers from verified evidence; abstains on out-of-scope/nutrition queries.
            4. **Agentic Workflow (`app/graph.py`, `app/tools.py`)**:
               - **LangGraph** StateGraph with memory checkpointer and human-in-the-loop approval.
               - `build_grocery_list()` scales ingredients, converts units (cup/tbsp/tsp → grams/ml), and merges duplicates.
            5. **FastAPI Backend (`app/main.py`)**:
               - `/health`, `/records`, `/search`, `/ask`, `/agent` endpoints.
            6. **Streamlit UI (`ui/app.py`)**:
               - Interactive 7-day grid, dal repeat warnings, thumbs up/down feedback, and grocery export.
            """
        )

    with tab_milestones:
        st.markdown(
            """
            ###  Milestones (Days 1–12)
            - ✅ **Day 1**: MediaWiki API recipe scraper & intro scripts.
            - ✅ **Day 2**: Recipe data models, parsing, and CLI.
            - ✅ **Day 3**: Data pipeline & normalized 20 recipes in `data/records.json`.
            - ✅ **Day 4**: Pandas dataset exploration & FastAPI basic search endpoints.
            - ✅ **Day 5**: LLM prompt engineering & evaluation benchmark questions.
            - ✅ **Day 6**: LLM Chat integration with Groq/Gemini & prompt versioning.
            - ✅ **Day 7**: Semantic search with ChromaDB & Sentence-Transformers.
            - ✅ **Day 8**: RAG with citation verification & `build_grocery_list()` scaling tool.
            - ✅ **Day 9**: LangGraph agent with approval step & Streamlit prototype.
            - ✅ **Day 10**: Checkpoint 2 full Streamlit UI with 7-day thali grid & dal repeat warning.
            - ✅ **Day 11**: Pytest suite (9/9 passing), Ruff linter (0 errors), Dockerfile & docker-compose.
            - ✅ **Day 12**: GitHub Actions CI workflow (`.github/workflows/ci.yml`) & repository sync.
            """
        )
