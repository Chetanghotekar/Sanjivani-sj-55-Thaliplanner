"""Day 9 (S2): the same agent rebuilt as a LangGraph graph.

What LangGraph adds over app/agent_loop.py:
  * memory      - a checkpointer saves the state per thread_id, so a follow-up message
                  on the same thread remembers earlier turns.
  * approval    - the graph pauses (interrupt) before build_grocery_list and waits for
                  the person to approve or reject it.

Flow:  start -> decide -> (search_recipes) act -> decide ...
                       -> (build_grocery_list) approval -> act | reject -> decide
                       -> (final_answer) finish -> END
"""
from __future__ import annotations

import uuid
from typing import Any, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.agent_loop import MAX_STEPS, decide, execute_tool

LIMIT_MESSAGE = "I could not finish this in the allowed number of steps. Please try a simpler request."


class AgentStateError(Exception):
    """The request does not fit the thread's current state (for example, approving nothing)."""


class AgentState(TypedDict, total=False):
    history: list[dict]       # MEMORY: earlier turns on this thread {"user", "assistant"}
    goal: str                 # the current message
    steps: list[dict]         # tool calls made during the current turn
    pending: dict             # the action the model chose last
    approved: bool
    iterations: int
    answer: str
    grocery_list: dict | None
    stopped: str


# ---------------------------------------------------------------- nodes
def start_node(state: AgentState) -> dict:
    """Reset the per-turn fields; keep `history` (the memory)."""
    return {"steps": [], "pending": {}, "approved": False, "iterations": 0,
            "answer": "", "grocery_list": None, "stopped": "",
            "history": state.get("history") or []}


def decide_node(state: AgentState) -> dict:
    if state["iterations"] >= MAX_STEPS:
        return {"pending": {"action": "final_answer", "args": {"answer": LIMIT_MESSAGE}, "thought": ""},
                "stopped": "max_steps"}
    action = decide(state["goal"], state["steps"], state.get("history"))
    return {"pending": action, "iterations": state["iterations"] + 1}


def invalid_node(state: AgentState) -> dict:
    error = state["pending"].get("error", "invalid action") + ". Reply with one valid JSON action."
    step = {"action": "invalid", "args": {}, "observation": {"error": error}}
    return {"steps": state["steps"] + [step]}


def approval_node(state: AgentState) -> dict:
    """Pause here. The graph resumes when the caller sends Command(resume=True/False)."""
    args = state["pending"]["args"]
    decision = interrupt({
        "type": "approval_request",
        "tool": "build_grocery_list",
        "args": args,
        "message": "Approve building a shopping list for these recipes and servings?",
    })
    return {"approved": bool(decision)}


def reject_node(state: AgentState) -> dict:
    pending = state["pending"]
    step = {"action": pending["action"], "args": pending["args"], "thought": pending.get("thought", ""),
            "observation": {"error": "The person rejected this list. Ask what they want to change."}}
    return {"steps": state["steps"] + [step]}


def act_node(state: AgentState) -> dict:
    pending = state["pending"]
    observation = execute_tool(pending["action"], pending["args"])
    step = {"action": pending["action"], "args": pending["args"],
            "thought": pending.get("thought", ""), "observation": observation}
    update: dict[str, Any] = {"steps": state["steps"] + [step]}
    if pending["action"] == "build_grocery_list" and "error" not in observation:
        update["grocery_list"] = observation
    return update


def finish_node(state: AgentState) -> dict:
    answer = str(state["pending"]["args"]["answer"]).strip()
    turn = {"user": state["goal"], "assistant": answer}
    return {"answer": answer, "history": (state.get("history") or []) + [turn],
            "stopped": state.get("stopped") or "final_answer"}


# ---------------------------------------------------------------- routing
def route_after_decide(state: AgentState) -> str:
    action = state["pending"]["action"]
    if action == "final_answer":
        return "finish"
    if action == "invalid":
        return "invalid"
    if action == "build_grocery_list":
        return "approval"
    return "act"


def route_after_approval(state: AgentState) -> str:
    return "act" if state.get("approved") else "reject"


# ---------------------------------------------------------------- graph
def build_graph(checkpointer=None):
    graph = StateGraph(AgentState)
    graph.add_node("start", start_node)
    graph.add_node("decide", decide_node)
    graph.add_node("invalid", invalid_node)
    graph.add_node("approval", approval_node)
    graph.add_node("reject", reject_node)
    graph.add_node("act", act_node)
    graph.add_node("finish", finish_node)

    graph.add_edge(START, "start")
    graph.add_edge("start", "decide")
    graph.add_conditional_edges("decide", route_after_decide,
                                {"finish": "finish", "invalid": "invalid", "approval": "approval", "act": "act"})
    graph.add_conditional_edges("approval", route_after_approval, {"act": "act", "reject": "reject"})
    graph.add_edge("invalid", "decide")
    graph.add_edge("reject", "decide")
    graph.add_edge("act", "decide")
    graph.add_edge("finish", END)
    # InMemorySaver keeps memory while the server runs; it is lost on restart.
    return graph.compile(checkpointer=checkpointer or InMemorySaver())


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# ---------------------------------------------------------------- one API turn
def _pending_approval(graph, config) -> dict | None:
    snapshot = graph.get_state(config)
    for task in snapshot.tasks:
        for pending in task.interrupts:
            return pending.value
    return None


def run_turn(message: str | None = None, thread_id: str | None = None,
             approve: bool | None = None) -> dict[str, Any]:
    """Run one request on a thread: either a new message, or an approve/reject decision."""
    graph = get_graph()
    thread_id = thread_id or uuid.uuid4().hex
    config = {"configurable": {"thread_id": thread_id}}
    waiting = _pending_approval(graph, config)

    if approve is not None:
        if waiting is None:
            raise AgentStateError("Nothing is waiting for approval on this thread.")
        graph.invoke(Command(resume=bool(approve)), config)
    else:
        if not message or not message.strip():
            raise ValueError("message cannot be empty")
        if waiting is not None:
            raise AgentStateError("A shopping list is waiting for approval. Send approve true or false first.")
        graph.invoke({"goal": message.strip()}, config)

    pending = _pending_approval(graph, config)
    values = graph.get_state(config).values
    return {
        "thread_id": thread_id,
        "status": "awaiting_approval" if pending else "done",
        "answer": "" if pending else values.get("answer", ""),
        "pending_approval": pending,
        "grocery_list": values.get("grocery_list"),
        "steps": values.get("steps", []),
        "turns_remembered": len(values.get("history", [])),
    }
