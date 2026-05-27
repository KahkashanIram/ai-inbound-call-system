# app/graph/agent_graph.py

"""
🧠 AGENT GRAPH — LANGGRAPH ORCHESTRATOR (LAYER 15)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 PURPOSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Defines the LangGraph workflow for Agentic AI.

Controls:
- Node registration
- Execution flow
- Decision routing

Acts as:
👉 Central brain orchestrator


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 FLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User Input (GraphState)
   ↓
Planner (LLM decision)
   ↓
[Conditional Routing]
   ├── Tool Node (if action required)
   └── Responder (direct response)
   ↓
Responder (final output)
   ↓
END


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 DESIGN PRINCIPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Pure orchestration (NO business logic)
- Deterministic flow
- Easily extensible
- Async compatible
"""

from langgraph.graph import StateGraph, END

from app.graph.state import GraphState
from app.graph.nodes.planner import planner_node
from app.graph.nodes.tool_node import tool_node

# ✅ STEP 4 — IMPORT REAL RESPONDER NODE
from app.graph.nodes.responder import responder_node


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔀 ROUTING LOGIC (CORE OF AGENT)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def route_planner(state: GraphState):
    """
    Decides next step after planner

    If planner decides to call tool → go to tool node
    Otherwise → go to responder
    """
    if state.get("decision") == "call_tool":
        return "tool"
    return "responder"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧠 GRAPH BUILDER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_agent_graph():
    """
    Builds and compiles the LangGraph agent
    """

    graph = StateGraph(GraphState)

    # ───────────────────────────────────
    # Register Nodes
    # ───────────────────────────────────
    graph.add_node("planner", planner_node)
    graph.add_node("tool", tool_node)

    # ✅ STEP 4 — USE REAL RESPONDER (REPLACES PLACEHOLDER)
    graph.add_node("responder", responder_node)

    # ───────────────────────────────────
    # Entry Point
    # ───────────────────────────────────
    graph.set_entry_point("planner")

    # ───────────────────────────────────
    # Conditional Routing (Planner → Next Step)
    # ───────────────────────────────────
    graph.add_conditional_edges(
        "planner",
        route_planner,
        {
            "tool": "tool",
            "responder": "responder"
        }
    )

    # ───────────────────────────────────
    # Tool → Responder
    # ───────────────────────────────────
    graph.add_edge("tool", "responder")

    # ───────────────────────────────────
    # End Flow
    # ───────────────────────────────────
    graph.add_edge("responder", END)

    return graph.compile()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🚀 GRAPH INSTANCE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

agent_graph = build_agent_graph()