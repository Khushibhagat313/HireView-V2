from langgraph.graph import StateGraph, START, END

from src.agents.conversation.state import HiringState
from src.agents.conversation.router import classify_intent
from src.agents.conversation.handlers import (
    show_top_n,
    filter_by_skill,
    filter_by_experience,
    hidden_gems,
    explain_score,
    compare,
    interview_questions,
    general,
)

HANDLERS = {
    "show_top_n": show_top_n,
    "filter_by_skill": filter_by_skill,
    "filter_by_experience": filter_by_experience,
    "hidden_gems": hidden_gems,
    "explain_score": explain_score,
    "compare": compare,
    "interview_questions": interview_questions,
    "general": general,
}


def route_by_intent(state: HiringState) -> str:
    return state["intent"]


def build_graph():
    graph = StateGraph(HiringState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_edge(START, "classify_intent")

    for name, handler in HANDLERS.items():
        graph.add_node(name, handler)
        graph.add_edge(name, END)

    graph.add_conditional_edges("classify_intent", route_by_intent, {name: name for name in HANDLERS})

    return graph.compile()