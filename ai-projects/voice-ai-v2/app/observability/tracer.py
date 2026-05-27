# app/observability/tracer.py

import time
import uuid
from typing import Dict, Any, List
from collections import defaultdict


class TraceManager:
    """
    🧠 Central Observability Engine

    Tracks:
    - Node execution
    - Inputs / outputs
    - Timing
    - Call lifecycle
    - Latency spans (NEW 🔥)
    """

    def __init__(self):
        # 🔥 Call-level logs
        self.traces: Dict[str, List[Dict[str, Any]]] = {}

        # 🔥 Latency spans per call
        # {call_id: {span_name: {start, end, duration}}}
        self.spans: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)

    # =========================
    # 🚀 START TRACE
    # =========================
    def start_trace(self, call_id: str) -> str:
        trace_id = str(uuid.uuid4())

        self.traces[call_id] = []
        self.spans[call_id] = {}

        return trace_id

    # =========================
    # 🧠 LOG NODE EXECUTION
    # =========================
    def log(
        self,
        call_id: str,
        node: str,
        input_data: Any = None,
        output_data: Any = None,
        metadata: Dict[str, Any] = None,
    ):
        entry = {
            "timestamp": time.time(),
            "node": node,
            "input": input_data,
            "output": output_data,
            "metadata": metadata or {},
        }

        if call_id not in self.traces:
            self.traces[call_id] = []

        self.traces[call_id].append(entry)

    # =========================
    # ⏱️ START SPAN (NEW 🔥)
    # =========================
    def start_span(self, call_id: str, span_name: str):
        self.spans[call_id][span_name] = {
            "start": time.time(),
            "end": None,
            "duration": None,
        }

    # =========================
    # ⏱️ END SPAN (NEW 🔥)
    # =========================
    def end_span(self, call_id: str, span_name: str):
        span = self.spans[call_id].get(span_name)

        if not span or span["start"] is None:
            return

        span["end"] = time.time()
        span["duration"] = round(span["end"] - span["start"], 3)

        # 🔥 Console debug (can later go to logger)
        print(f"⏱️ [{call_id}] {span_name}: {span['duration']}s")

    # =========================
    # 📜 GET TRACE
    # =========================
    def get_trace(self, call_id: str):
        return {
            "logs": self.traces.get(call_id, []),
            "spans": self.spans.get(call_id, {}),
        }

    # =========================
    # 📊 GET ALL CALLS
    # =========================
    def get_all_calls(self):
        return list(self.traces.keys())

    # =========================
    # 📊 GET ACTIVE SPANS (OPTIONAL)
    # =========================
    def get_spans(self, call_id: str):
        return self.spans.get(call_id, {})

    # =========================
    # 🧹 CLEAR TRACE (OPTIONAL)
    # =========================
    def clear_trace(self, call_id: str):
        self.traces.pop(call_id, None)
        self.spans.pop(call_id, None)


# 🔥 GLOBAL INSTANCE (SINGLE SOURCE OF TRUTH)
trace_manager = TraceManager()