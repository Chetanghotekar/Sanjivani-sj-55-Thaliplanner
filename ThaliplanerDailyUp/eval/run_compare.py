"""Day 6: run the 10 questions through prompt v1 and v2 and fill the results table.

Usage (from project root, with .env set):
    python -m eval.run_compare
It rewrites the results section of eval/prompt_compare.md.
"""
from pathlib import Path
from app.main import run_chat
from app.llm import LLMError

DOC = Path(__file__).with_name("prompt_compare.md")
MARKER = "<!-- RESULTS -->"

QUESTIONS = [
    ("answer", "What ingredients do I need for Moong Dal?"),
    ("answer", "How long does Khichdi take and is it easy?"),
    ("answer", "Which recipes in your data use coconut?"),
    ("answer", "Can I make Idli without urad dal?"),
    ("answer", "Is Paneer Butter Masala vegan?"),
    ("answer", "Give me the exact steps and gram quantities for Dhokla."),
    ("plan", "Plan a vegetarian South Indian thali for 4 people."),
    ("plan", "Suggest a light thali for dinner with dal and rice."),
    ("answer", "What is the capital of France?"),
    ("answer", "I have diabetes, which dal should I eat to cure it?"),
]


def cell(text: str) -> str:
    return text.replace("|", "/").replace("\n", " ").strip()


def main():
    rows = ["| # | Task | Question | v1 answer | v1 conf. | v2 answer | v2 conf. | v2 follow_up |",
            "|---|------|----------|-----------|----------|-----------|----------|--------------|"]
    for i, (task, q) in enumerate(QUESTIONS, 1):
        out = {}
        for version in ("v1", "v2"):
            try:
                r = run_chat(q, task, version)
                out[version] = (cell(r.answer), r.confidence, cell(r.follow_up))
            except LLMError as exc:
                out[version] = (f"ERROR: {cell(str(exc))}", "-", "")
        rows.append(f"| {i} | {task} | {cell(q)} | {out['v1'][0]} | {out['v1'][1]} | "
                    f"{out['v2'][0]} | {out['v2'][1]} | {out['v2'][2]} |")
    text = DOC.read_text(encoding="utf-8")
    head = text.split(MARKER)[0]
    DOC.write_text(head + MARKER + "\n\n" + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"Wrote results to {DOC}")


if __name__ == "__main__":
    main()
