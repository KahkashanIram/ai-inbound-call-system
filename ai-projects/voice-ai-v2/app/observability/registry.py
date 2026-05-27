# app/observability/registry.py

import time
from typing import Dict, Any


class ActiveCallRegistry:
    """
    📊 Tracks all active calls in real-time

    Used for:
    - Dashboard
    - Multi-call graph
    - System monitoring
    """

    def __init__(self):
        self.calls: Dict[str, Dict[str, Any]] = {}

    # =========================
    # 🚀 START CALL
    # =========================
    def start_call(self, call_id: str):
        self.calls[call_id] = {
            "call_id": call_id,
            "status": "active",
            "current_node": "start",
            "start_time": time.time(),
            "last_update": time.time()
        }

    # =========================
    # 🔄 UPDATE NODE
    # =========================
    def update_node(self, call_id: str, node: str):
        if call_id in self.calls:
            self.calls[call_id]["current_node"] = node
            self.calls[call_id]["last_update"] = time.time()

    # =========================
    # 🛑 END CALL
    # =========================
    def end_call(self, call_id: str):
        if call_id in self.calls:
            self.calls[call_id]["status"] = "completed"
            self.calls[call_id]["last_update"] = time.time()

    # =========================
    # 📊 GET ALL
    # =========================
    def get_all(self):
        return list(self.calls.values())

    # =========================
    # 🔍 GET ONE
    # =========================
    def get(self, call_id: str):
        return self.calls.get(call_id)

    # ==================================================
    # 🔥 NEW: TOTAL CALLS (REQUIRED FOR QUEUE LOGIC)
    # ==================================================
    @property
    def total_calls(self) -> int:
        """
        🚀 Returns total active calls

        Used in:
        - NON_BLOCKING_MODE trigger
        - Load balancing
        """
        return len(self.calls)

    # ==================================================
    # 🔥 NEW: ACTIVE CALL COUNT (DASHBOARD READY)
    # ==================================================
    def active_count(self) -> int:
        """
        📊 Counts only ACTIVE calls

        Future use:
        - Dashboard metrics
        - Load visualization
        """
        return sum(1 for c in self.calls.values() if c["status"] == "active")

    # ==================================================
    # 🔥 NEW: CLEANUP STALE CALLS (PRODUCTION SAFETY)
    # ==================================================
    def cleanup_stale_calls(self, timeout: int = 300):
        """
        🧹 Removes stale calls (failsafe)

        - Prevents memory leak
        - Handles unexpected disconnects

        Args:
            timeout (seconds): inactivity threshold
        """
        now = time.time()

        to_delete = [
            call_id for call_id, call in self.calls.items()
            if now - call["last_update"] > timeout
        ]

        for call_id in to_delete:
            print(f"🧹 CLEANUP STALE CALL: {call_id}")
            self.calls.pop(call_id, None)


# 🔥 GLOBAL INSTANCE
active_call_registry = ActiveCallRegistry()