# app/graph/state.py

"""
🧠 GRAPH STATE — LANGGRAPH EXECUTION MEMORY (LAYER 15)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 POSITION IN SYSTEM ARCHITECTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User Speech
   ↓
Twilio (Media Stream)
   ↓
Deepgram STT
   ↓
Transcript (TEXT)
   ↓
🧠 GraphState (THIS FILE)  ← ENTRY POINT TO AGENTIC LAYER
   ↓
LangGraph Execution:
    ├── Planner Node
    ├── Tool Node (optional)
    ├── Responder Node
   ↓
Final Response (TEXT)
   ↓
Deepgram TTS
   ↓
Twilio Audio Stream


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 PURPOSE OF THIS FILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file defines the **state object that flows through the LangGraph system**.

It acts as:
👉 "Execution memory for a single conversational turn"

Each node in the graph:
- Reads from this state
- Modifies it
- Passes it forward

⚠️ IMPORTANT:
- This is NOT session memory (CallState handles that)
- This is NOT persistent
- This is ONLY for one execution cycle


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 DESIGN PRINCIPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Typed → Predictable + Debuggable
2. Minimal → Avoid unnecessary coupling
3. Extensible → Supports future multi-step reasoning
4. Serializable → Required for LangGraph execution


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚫 WHAT THIS FILE MUST NEVER DO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- ❌ No Twilio logic
- ❌ No Deepgram logic
- ❌ No database access
- ❌ No business logic
- ❌ No tool execution

This file is PURE DATA STRUCTURE.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from typing import TypedDict, Optional, Dict, Any


class GraphState(TypedDict, total=False):
    """
    🧠 Graph Execution State (Single Turn)

    This object flows across ALL nodes in LangGraph.

    Lifecycle:
    ----------
    1. Created when transcript arrives
    2. Passed into Planner
    3. Possibly enriched with tool decision
    4. Tool executes (optional)
    5. Final response generated
    6. Returned to TTS layer

    Each node:
    ----------
    - Reads existing keys
    - Updates relevant fields
    - NEVER wipes entire state
    """

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🎤 INPUT LAYER
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    user_input: str
    """
    Clean transcript from Deepgram

    Source:
    - Deepgram streaming STT

    Example:
    "I want to place an order for 5 units of item A"

    This is the ONLY required input to start graph execution.
    """

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🧠 PLANNER OUTPUT (LLM DECISION LAYER)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    decision: str
    """
    Decision made by Planner node (LLM)

    Possible values (controlled vocabulary):
    - "respond"            → Direct answer, no tool needed
    - "call_tool"          → Requires tool execution
    - "ask_clarification"  → Missing info from user

    This drives graph routing.
    """

    tool_name: Optional[str]
    """
    Name of the tool selected by Planner

    Example:
    - "create_order"
    - "check_order_status"

    None if no tool is required.
    """

    tool_args: Optional[Dict[str, Any]]
    """
    Structured arguments extracted by LLM for tool execution

    Example:
    {
        "item_code": "X123",
        "quantity": 5
    }

    IMPORTANT:
    - Must be JSON-serializable
    - Must match tool schema
    """

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🔧 TOOL EXECUTION OUTPUT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    tool_result: Optional[Dict[str, Any]]
    """
    Output returned from tool execution layer

    Source:
    - OrderService or other tools

    Example:
    {
        "order_id": "ORD-001",
        "status": "confirmed"
    }

    This is later used by Responder node.
    """

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 💬 FINAL RESPONSE LAYER
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    response: Optional[str]
    """
    Final response text generated for the user

    This is:
    - Natural language
    - Ready for TTS
    - No further processing needed

    Example:
    "Your order has been successfully placed."
    """

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🔁 CONTROL / FLOW MANAGEMENT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    is_complete: Optional[bool]
    """
    Indicates whether graph execution is complete

    Used for:
    - Future multi-step loops
    - Advanced agent recursion
    - Debugging flow completion

    For now:
    - Set True at end of responder
    """