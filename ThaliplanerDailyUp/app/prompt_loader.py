"""Day 6: Load prompt text from the prompts/ folder."""
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"

# v1 = short baseline prompt, v2 = full system prompt + a task prompt.
TASKS = {"answer": "task_answer.md", "plan": "task_plan.md"}


def read_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


def build_system_prompt(version: str, task: str) -> str:
    if version == "v1":
        return read_prompt("system_v1.md")
    if task not in TASKS:
        raise ValueError(f"Unknown task '{task}'. Use one of: {', '.join(TASKS)}")
    return read_prompt("system.md") + "\n\n" + read_prompt(TASKS[task])
