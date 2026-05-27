# app/graph/nodes/responder.py

import asyncio
import time

from app.graph.state import GraphState
from app.observability.tracer import trace_manager
from app.observability.registry import active_call_registry
from app.services.llm_service import LLMService
from app.core.prompt_manager import prompt_manager


llm = LLMService()

# 🔥 CIRCUIT BREAKER STATE
LLM_FAILURES = 0
LLM_DISABLED_UNTIL = 0


# =========================
# 🧠 GOODBYE DETECTION
# =========================
def is_goodbye(text: str) -> bool:
    if not text:
        return False

    text = text.lower().strip()

    return any(phrase in text for phrase in [
        "no", "no thanks", "no thank you", "nothing",
        "nothing else", "that's all", "i'm done",
        "all good", "bye", "bye bye", "thank you", "thanks"
    ])


# =========================
# 🤖 SAFE LLM CALL (ENTERPRISE)
# =========================
async def safe_llm_call(prompt: str, call_id: str, timeout=2.5, retries=2):

    global LLM_FAILURES, LLM_DISABLED_UNTIL

    # 🔥 CIRCUIT BREAKER CHECK
    if time.time() < LLM_DISABLED_UNTIL:
        raise Exception("LLM disabled (circuit breaker active)")

    for attempt in range(retries + 1):
        try:
            result = await asyncio.wait_for(
                llm.generate(prompt, call_id),
                timeout=timeout
            )

            LLM_FAILURES = 0
            return result

        except Exception as e:
            print(f"⚠️ LLM attempt {attempt+1} failed: {e}")
            LLM_FAILURES += 1
            await asyncio.sleep(0.3 * (attempt + 1))

    # 🔥 ACTIVATE CIRCUIT BREAKER
    if LLM_FAILURES >= 5:
        LLM_DISABLED_UNTIL = time.time() + 10
        print("🚨 RESPONDER CIRCUIT BREAKER ACTIVATED")

    raise Exception("LLM failed after retries")


# =========================
# 🧠 RESPONDER NODE (ENTERPRISE)
# =========================
async def responder_node(state: GraphState) -> GraphState:

    call_id = state.get("call_id", "unknown")
    user_input = state.get("input") or state.get("user_input") or ""

    decision = state.get("decision", "respond")
    tool_name = state.get("tool_name")
    tool_result = state.get("tool_result") or {}

    memory = state.get("memory") or {}

    active_call_registry.update_node(call_id, "responder")

    # ⏱️ LATENCY START
    trace_manager.start_span(call_id, "responder")
    start_time = time.time()

    trace_manager.log(
        call_id,
        "responder_start",
        input_data={
            "decision": decision,
            "tool": tool_name,
            "has_tool_result": bool(tool_result)
        }
    )

    try:

        # =========================
        # 🚨 CASE 0 — FORCED RESPONSE
        # =========================
        if state.get("force_response"):
            response = state["force_response"]
            source = "force"

        # =========================
        # 👋 CASE 1 — GOODBYE
        # =========================
        elif is_goodbye(user_input):
            try:
                prompt = prompt_manager.get("goodbye.txt")
                response = await safe_llm_call(prompt, call_id)
            except Exception:
                response = "Thank you for calling. Have a great day."

            state["is_complete"] = True
            source = "goodbye"

        # =========================
        # 🔧 CASE 2 — TOOL RESPONSE
        # =========================
        elif decision == "call_tool" and tool_name == "check_order_status":

            try:
                template = prompt_manager.get("order_tracking.txt")

                prompt = template.replace(
                    "{{ORDER_DATA}}",
                    str(tool_result)
                )

                response = await safe_llm_call(prompt, call_id)

                if not response:
                    raise Exception("Empty response")

            except Exception as e:
                print(f"❌ TOOL ERROR: {e}")

                status = tool_result.get("status", "unknown")
                location = tool_result.get("location", "unknown location")

                response = f"Your order is {status} at {location}."

            response = response.strip() + " Is there anything else I can help you with?"
            state["is_complete"] = False
            source = "tool"

        # =========================
        # 💬 CASE 3 — GENERAL RESPONSE
        # =========================
        else:
            try:
                base_prompt = prompt_manager.get("general_response.txt")
                guardrails = prompt_manager.get("response_guardrails.txt")
            except Exception:
                base_prompt = ""
                guardrails = ""

            prompt = f"""
{guardrails}

{base_prompt}

User: {user_input}
Memory: {memory}
"""

            try:
                response = await safe_llm_call(prompt, call_id)

                if not response:
                    raise Exception("Empty response")

            except Exception as e:
                print(f"❌ GENERAL RESPONSE ERROR: {e}")
                response = "I'm sorry, I didn't understand that."

            response = response.strip() + " Is there anything else I can help you with?"
            state["is_complete"] = False
            source = "llm"

        # =========================
        # 🧼 SANITIZE RESPONSE
        # =========================
        if not isinstance(response, str) or not response.strip():
            response = "Could you please repeat that?"
            source = "fallback"

        state["response"] = response.strip()

        # =========================
        # 🧠 MEMORY UPDATE
        # =========================
        state.setdefault("memory", {})
        state["memory"]["last_user"] = user_input
        state["memory"]["last_response"] = response

    except Exception as e:
        print(f"🚨 RESPONDER CRITICAL ERROR: {e}")
        state["response"] = "System error occurred. Please try again."
        state["is_complete"] = False
        source = "critical"

    # =========================
    # 📊 TRACE + DEBUG
    # =========================
    latency = round(time.time() - start_time, 3)

    trace_manager.log(
        call_id,
        "responder_end",
        output_data={
            "response": state["response"],
            "source": source,
            "latency": latency
        }
    )

    trace_manager.end_span(call_id, "responder")

    print(f"""
📤 RESPONDER DEBUG
Call: {call_id}
Source: {source}
Latency: {latency}s
Response: {state['response']}
""")

    return state