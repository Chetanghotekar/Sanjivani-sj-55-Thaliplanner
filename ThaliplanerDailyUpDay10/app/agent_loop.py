"""Day 9 (S1): a hand-written agent loop.

The model never runs anything itself. Each step it replies with one JSON action;
this file runs the matching tool, shows the model the result, and repeats until the
model gives final_answer or the step limit is reached. app/graph.py reuses the
helpers below, so both versions behave the same.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from app.llm import LLMError, ask_llm
from app.prompt_loader import read_prompt
from app.tools import build_grocery_list, search_recipes

MAX_STEPS = 6
OBSERVATION_LIMIT = 2500  # characters of tool output shown back to the model

TOOLS: dict[str, Callable[..., dict]] = {
    "search_recipes": search_recipes,
    "build_grocery_list": build_grocery_list,
}
ACTIONS = set(TOOLS) | {"final_answer"}


# ---------------------------------------------------------------- shared helpers
def system_prompt() -> str:
    return read_prompt("agent_system.md")


def parse_action(raw: str) -> dict[str, Any]:
    """Turn the model's reply into {"thought", "action", "args"}. Raises ValueError if unusable."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("reply is not a JSON object")
    data = json.loads(text[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("reply is not a JSON object")
    action = str(data.get("action", "")).strip()
    if action not in ACTIONS:
        raise ValueError(f"unknown action '{action}'. Use one of: {', '.join(sorted(ACTIONS))}")
    args = data.get("args") or {}
    if not isinstance(args, dict):
        raise ValueError("'args' must be a JSON object")
    return {"thought": str(data.get("thought", "")).strip(), "action": action, "args": args}


def check_tool_args(action: str, args: dict) -> str | None:
    """Return a problem description if the arguments are unusable, else None."""
    if action == "search_recipes":
        if not str(args.get("query", "")).strip():
            return "search_recipes needs a non-empty 'query'"
    elif action == "build_grocery_list":
        selections = args.get("selections")
        if not isinstance(selections, list) or not selections:
            return "build_grocery_list needs 'selections': a non-empty list of {recipe_id, servings}"
        for entry in selections:
            if not isinstance(entry, dict) or "recipe_id" not in entry:
                return "every selection needs a 'recipe_id'"
    elif action == "final_answer":
        if not str(args.get("answer", "")).strip():
            return "final_answer needs a non-empty 'answer'"
    return None


def execute_tool(action: str, args: dict) -> dict[str, Any]:
    """Run one tool and always return a dict (errors become {"error": ...}, never exceptions)."""
    try:
        return TOOLS[action](**args)
    except (ValueError, TypeError) as exc:
        return {"error": str(exc)}
    except Exception as exc:  # a tool bug must not crash the whole agent
        return {"error": f"{type(exc).__name__}: {exc}"}


def short(observation: dict) -> str:
    text = json.dumps(observation, ensure_ascii=False)
    if len(text) > OBSERVATION_LIMIT:
        text = text[:OBSERVATION_LIMIT] + " ...(truncated)"
    return text


def build_user_prompt(goal: str, steps: list[dict], history: list[dict] | None = None) -> str:
    """Everything the model needs for its next decision, as plain text."""
    parts = []
    if history:
        parts.append("EARLIER IN THIS CONVERSATION:")
        for turn in history[-5:]:
            parts.append(f"Person: {turn['user']}\nYou answered: {turn['assistant']}")
        parts.append("")
    parts.append(f"CURRENT REQUEST:\n{goal.strip()}")
    if steps:
        parts.append("\nSTEPS SO FAR:")
        for number, step in enumerate(steps, start=1):
            parts.append(f"{number}. action={step['action']} args={json.dumps(step['args'], ensure_ascii=False)}")
            parts.append(f"   result: {short(step['observation'])}")
    parts.append("\nReply with the next JSON action.")
    return "\n".join(parts)


def decide(goal: str, steps: list[dict], history: list[dict] | None = None) -> dict[str, Any]:
    """Ask the model for the next action. Returns a parsed action, or an 'invalid' marker."""
    raw = ask_llm(system_prompt(), build_user_prompt(goal, steps, history), json_mode=True, temperature=0.2)
    try:
        action = parse_action(raw)
    except ValueError as exc:  # json.JSONDecodeError is a ValueError
        return {"action": "invalid", "args": {}, "thought": "", "error": str(exc)}
    problem = check_tool_args(action["action"], action["args"])
    if problem:
        return {**action, "action": "invalid", "error": problem}
    return action


# ---------------------------------------------------------------- the loop
def run_agent(goal: str, max_steps: int = MAX_STEPS, history: list[dict] | None = None,
              approve: Callable[[dict], bool] | None = None) -> dict[str, Any]:
    """Run the agent until it answers or runs out of steps.

    approve: optional function called before build_grocery_list; return False to refuse.
    Returns {"answer", "steps", "grocery_list", "stopped"}.
    """
    goal = (goal or "").strip()
    if not goal:
        raise ValueError("goal cannot be empty")

    steps: list[dict] = []
    grocery_list = None
    for _ in range(max_steps):
        action = decide(goal, steps, history)
        name, args = action["action"], action["args"]

        if name == "final_answer":
            return {"answer": str(args["answer"]).strip(), "steps": steps,
                    "grocery_list": grocery_list, "stopped": "final_answer"}

        if name == "invalid":
            observation = {"error": action["error"] + ". Reply with one valid JSON action."}
            steps.append({"action": "invalid", "args": {}, "observation": observation})
            continue

        if name == "build_grocery_list" and approve is not None and not approve(action):
            observation = {"error": "The person rejected this list. Ask what they want to change."}
        else:
            observation = execute_tool(name, args)
            if name == "build_grocery_list" and "error" not in observation:
                grocery_list = observation
        steps.append({"action": name, "args": args, "thought": action["thought"], "observation": observation})

    return {"answer": "I could not finish this in the allowed number of steps. Please try a simpler request.",
            "steps": steps, "grocery_list": grocery_list, "stopped": "max_steps"}


if __name__ == "__main__":
    import sys
    question = " ".join(sys.argv[1:]) or "Plan moong dal and khichdi for 8 people and make a shopping list."
    try:
        result = run_agent(question, approve=lambda a: input(
            f"Approve {json.dumps(a['args'])}? [y/N] ").strip().lower() == "y")
    except LLMError as exc:
        raise SystemExit(f"LLM error: {exc}")
    for step in result["steps"]:
        print(f"- {step['action']} {json.dumps(step['args'])}")
    print("\n" + result["answer"])
    if result["grocery_list"]:
        for item in result["grocery_list"]["items"]:
            print(f"  {item['display']:>10}  {item['item']}")
