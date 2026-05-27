# app/graph/nodes/tool_node.py

from app.graph.state import GraphState
from app.services.order_service import OrderService

# 🔥 TRACE LOGGER
from app.observability.tracer import trace_manager

# 🔥 ACTIVE CALL REGISTRY
from app.observability.registry import active_call_registry


# =========================
# 🔧 INIT SERVICE
# =========================
order_service = OrderService()


# =========================
# 🔧 TOOL NODE
# =========================
async def tool_node(state: GraphState) -> GraphState:
    """
    🔧 TOOL NODE — PRODUCTION VERSION

    Responsibilities:
    - Execute backend tools
    - Handle errors safely
    - Maintain observability (trace + registry)
    """

    tool_name = state.get("tool_name")
    tool_args = state.get("tool_args", {})

    call_id = state.get("call_id", "unknown")

    # =========================
    # 🔥 OBSERVABILITY START
    # =========================
    active_call_registry.update_node(call_id, "tool")

    trace_manager.log(
        call_id=call_id,
        node="tool_start",
        input_data={
            "tool_name": tool_name,
            "tool_args": tool_args
        }
    )

    # =========================
    # 🛑 SAFETY CHECK
    # =========================
    if not tool_name:
        result = {"error": "No tool provided"}
        state["tool_result"] = result

        trace_manager.log(
            call_id=call_id,
            node="tool_end",
            output_data=result
        )
        return state

    # =========================
    # 🎯 TOOL EXECUTION
    # =========================
    try:

        # ─────────────────────────
        # 📦 ORDER STATUS TOOL
        # ─────────────────────────
        if tool_name == "check_order_status":

            order_id = tool_args.get("order_id")

            if not order_id:
                raise ValueError("Missing order_id")

            # ✅ FIX: correct method
            order = order_service.get_order(order_id)

            if not order:
                result = {
                    "status": "not_found",
                    "order_id": order_id
                }
            else:
                result = {
                    "order_id": order.get("order_id"),
                    "status": order.get("status"),
                    "location": order.get("location"),
                    "eta": order.get("eta")
                }

        # ─────────────────────────
        # 📞 ESCALATION TOOL
        # ─────────────────────────
        elif tool_name == "escalate_to_human":
            result = {
                "status": "escalated",
                "reason": tool_args.get("reason", "not specified")
            }

        # ─────────────────────────
        # ❓ UNKNOWN TOOL
        # ─────────────────────────
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        print(f"❌ TOOL ERROR: {e}")
        result = {"error": str(e)}

    # =========================
    # 🧠 SAVE RESULT
    # =========================
    state["tool_result"] = result

    # =========================
    # 🔥 OBSERVABILITY END
    # =========================
    trace_manager.log(
        call_id=call_id,
        node="tool_end",
        output_data=result
    )

    return state