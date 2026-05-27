"""
📦 CALL STATE — ENTERPRISE GRADE (v6.0)

Enhancements:
- ✅ Follow-up control (prevents duplicate prompts)
- ✅ Meta memory (LangGraph-ready)
- ✅ Thread-safe updates
- ✅ Safe history + lifecycle tracking
"""

import asyncio
import time
from app.memory.store import MemoryManager


# 🔒 GLOBAL MEMORY MANAGER
memory_manager = MemoryManager()


class CallState:
    """
    Represents a single active call session (enterprise-safe)
    """

    def __init__(self, call_sid: str):
        self.call_sid = call_sid

        # =========================
        # 🧠 MEMORY (ATTACHED)
        # =========================
        self._memory = memory_manager.get(call_sid)

        # 🔥 ENSURE META EXISTS (CRITICAL FIX)
        if "meta" not in self._memory:
            self._memory["meta"] = {}

        # =========================
        # 🔐 CONCURRENCY CONTROL
        # =========================
        self._lock = asyncio.Lock()

        # =========================
        # 📊 STATE
        # =========================
        self.is_active = True
        self.is_speaking = False

        self.last_user_input = None
        self.last_ai_response = None

        # 🔥 FOLLOW-UP CONTROL (FIX)
        self.followup_asked = False

        # =========================
        # ⏱️ LIFECYCLE TRACKING
        # =========================
        self.created_at = time.time()
        self.last_updated = time.time()

    # =========================
    # 🧠 MEMORY ACCESS (SAFE)
    # =========================
    def get_memory(self):
        return self._memory

    async def safe_update_memory(self, update_fn):
        """
        Thread-safe memory mutation
        """
        async with self._lock:
            update_fn(self._memory)
            self.last_updated = time.time()

    def reset_memory(self):
        memory_manager.clear(self.call_sid)

    # =========================
    # 🔄 STATE MANAGEMENT
    # =========================
    async def set_user_input(self, text: str):
        async with self._lock:
            self.last_user_input = text
            self.last_updated = time.time()

    async def set_ai_response(self, text: str):
        async with self._lock:
            self.last_ai_response = text
            self.last_updated = time.time()

            # 🔥 SAFE HISTORY UPDATE
            try:
                if self.last_user_input:
                    self._memory["history"].add(
                        self.last_user_input,
                        self.last_ai_response
                    )
            except Exception as e:
                print(f"⚠️ Memory history error: {e}")

    # =========================
    # 🧠 FOLLOW-UP CONTROL
    # =========================
    def mark_followup_asked(self):
        """
        Mark that follow-up question was already asked
        """
        self.followup_asked = True
        self._memory["meta"]["followup_asked"] = True

    def has_asked_followup(self):
        """
        Check if follow-up already asked
        """
        return self.followup_asked or self._memory["meta"].get("followup_asked", False)

    # =========================
    # 📊 HEALTH CHECK
    # =========================
    def is_stale(self, timeout=300):
        """
        Detect inactive sessions
        """
        return (time.time() - self.last_updated) > timeout

    # =========================
    # 🛑 CLEANUP
    # =========================
    def end_call(self):
        self.is_active = False
        self.followup_asked = False

        try:
            memory_manager.clear(self.call_sid)
        except Exception as e:
            print(f"⚠️ Memory cleanup error: {e}")