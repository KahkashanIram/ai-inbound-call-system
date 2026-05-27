# app/graph/nodes/planner.py

import json
import re
import asyncio
import time
from typing import Dict, Any

from app.observability.tracer import trace_manager
from app.observability.registry import active_call_registry

from app.graph.state import GraphState
from app.services.llm_service import LLMService
from app.core.prompt_manager import prompt_manager


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🤖 INIT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

llm_service = LLMService()

# 🔥 Circuit breaker state (simple in-memory)
LLM_FAILURES = 0
LLM_DISABLED_UNTIL = 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧠 JSON VALIDATION (STRICT)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def validate_llm_output(parsed: Dict[str, Any]) -> Dict[str, Any]:
    decision = parsed.get("decision", "respond")
    tool_name = parsed.get("tool_name")
    tool_args = parsed.get("tool_args", {})
    confidence = parsed.get("confidence", 0.7)

    if decision not in ["respond", "call_tool"]:
        decision = "respond"

    if decision == "call_tool" and not tool_name:
        tool_name = "check_order_status"

    if not isinstance(tool_args, dict):
        tool_args = {}

    return {
        "decision": decision,
        "tool_name": tool_name,
        "tool_args": tool_args,
        "confidence": float(confidence)
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔧 ORDER ID DETECTOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detect_order_id(text: str):
    text = text.upper().strip()
    text = re.sub(r"[^\w\s]", "", text)

    patterns = [
        r"\b[A-Z]{1,3}\d{3,6}\b",
        r"\b\d{3,6}\b"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group()

    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🤖 LLM CALL WITH RETRY + BACKOFF
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def call_llm_with_retry(prompt: str, call_id: str, retries=2, timeout=2.0):

    global LLM_FAILURES, LLM_DISABLED_UNTIL

    # 🔥 Circuit breaker check
    if time.time() < LLM_DISABLED_UNTIL:
        raise Exception("LLM temporarily disabled (circuit breaker)")

    for attempt in range(retries + 1):
        try:
            response = await asyncio.wait_for(
                llm_service.generate(prompt, call_id),
                timeout=timeout
            )

            LLM_FAILURES = 0  # reset on success
            return response

        except Exception as e:
            print(f"⚠️ LLM attempt {attempt+1} failed: {e}")
            LLM_FAILURES += 1
            await asyncio.sleep(0.3 * (attempt + 1))  # backoff

    # 🔥 Trigger circuit breaker
    if LLM_FAILURES >= 5:
        LLM_DISABLED_UNTIL = time.time() + 10
        print("🚨 LLM CIRCUIT BREAKER ACTIVATED")

    raise Exception("LLM failed after retries")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧠 SAFE JSON PARSE (ADDED HARDENING)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def safe_json_parse(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            return json.loads(text[start:end])
        except Exception:
            return {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧠 MAIN PLANNER NODE (ENTERPRISE)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def planner_node(state: GraphState) -> GraphState:

    user_input = state.get("input") or state.get("user_input") or ""
    call_id = state.get("call_id", "unknown")

    active_call_registry.update_node(call_id, "planner")

    trace_manager.start_span(call_id, "planner")

    trace_manager.log(call_id, "planner_start", input_data=user_input)

    # =========================
    # 🧠 INIT STATE
    # =========================

    state.setdefault("meta", {})
    state["meta"].setdefault("invalid_attempts", 0)

    # =========================
    # ⚡ FAST PATH (RULE ENGINE)
    # =========================

    order_id = detect_order_id(user_input)

    if order_id:
        result = {
            "decision": "call_tool",
            "tool_name": "check_order_status",
            "tool_args": {"order_id": order_id},
            "confidence": 0.99
        }
        state["meta"]["invalid_attempts"] = 0

    elif any(x in user_input.lower() for x in ["hi", "hello", "hey"]):
        state["force_response"] = "Hello! How can I assist you today?"
        result = {
            "decision": "respond",
            "tool_name": None,
            "tool_args": {},
            "confidence": 0.95
        }

    else:
        # =========================
        # 🤖 LLM FALLBACK (ENTERPRISE)
        # =========================

        base_prompt = prompt_manager.get("intent_router.txt")

        prompt = f"""
{base_prompt}

User: "{user_input}"

Return STRICT JSON:
{{
  "decision": "respond" | "call_tool",
  "tool_name": string or null,
  "tool_args": object,
  "confidence": float
}}
"""

        try:
            llm_output = await call_llm_with_retry(prompt, call_id)
            parsed = safe_json_parse(llm_output)

        except Exception as e:
            print(f"❌ LLM FAIL SAFE: {e}")
            parsed = {}

        result = validate_llm_output(parsed)

    # =========================
    # 🔁 RETRY LOGIC
    # =========================

    if not order_id:
        if "order" in user_input.lower() or state["meta"]["invalid_attempts"] > 0:
            state["meta"]["invalid_attempts"] += 1
            attempts = state["meta"]["invalid_attempts"]

            if attempts == 1:
                state["force_response"] = "Could you please share your order ID?"

            elif attempts == 2:
                state["force_response"] = "I didn’t catch that. Please repeat your order ID."

            elif attempts >= 3:
                state["force_response"] = "Please contact support. Thank you."
                state["decision"] = "respond"

                trace_manager.end_span(call_id, "planner")
                return state

    # =========================
    # 📦 UPDATE STATE
    # =========================

    state["decision"] = result["decision"]
    state["tool_name"] = result["tool_name"]
    state["tool_args"] = result["tool_args"]
    state["confidence"] = result["confidence"]

    # =========================
    # 📊 TRACE
    # =========================

    trace_manager.log(
        call_id,
        "planner_end",
        output_data=result,
        metadata={"confidence": result["confidence"]}
    )

    trace_manager.end_span(call_id, "planner")

    return state