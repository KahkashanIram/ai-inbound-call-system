# app/services/agent_handler.py

import json
import re
from pathlib import Path
from app.core.prompt_manager import prompt_manager
from app.services.order_service import OrderService



def load_prompt(name: str) -> str:
    """
    🚀 ENTERPRISE PROMPT LOADER (NON-BLOCKING)

    - Uses in-memory cache
    - No disk I/O during runtime
    """
    return prompt_manager.get(name)

class AgentHandler:
    def __init__(self, llm):
        print("🔥 USING SERVICES AGENT HANDLER")
        self.llm = llm
        self.order_service = OrderService()

    # =========================
    # 📄 LOAD PROMPT
    # =========================
   


    # =========================
    # 🧠 LLM CALL
    # =========================
    async def llm_call(self, prompt: str) -> str:
        try:
            return await self.llm.generate(prompt)
        except Exception as e:
            print(f"⚠️ LLM error: {e}")
            return ""

    # =========================
    # 🧠 PROMPT BUILDER
    # =========================
    def build_prompt(self, name: str, variables: dict):
        template = self.load_prompt(name)
        for k, v in variables.items():
            template = template.replace(f"{{{{{k}}}}}", str(v))
        return template

    # =========================
    # 🧠 INTENT ROUTER (LLM)
    # =========================
    async def route_intent(self, text: str) -> dict:
        try:
            prompt = self.build_prompt("intent_router.txt", {
                "USER_INPUT": text
            })

            raw = await self.llm_call(prompt)
            parsed = json.loads(raw)

            return {
                "intent": parsed.get("intent"),
                "confidence": parsed.get("confidence", 0)
            }

        except Exception:
            return {"intent": "general", "confidence": 0}

    # =========================
    # 🧠 ENTITY EXTRACTION
    # =========================
    async def extract(self, text: str) -> dict:
        try:
            prompt = self.build_prompt("memory_extraction.txt", {
                "USER_INPUT": text
            })

            raw = await self.llm_call(prompt)
            parsed = json.loads(raw)

            return parsed

        except Exception:
            return {
                "intent": None,
                "entities": {"order_id": None},
                "confidence": 0
            }

    # =========================
    # 🔥 ORDER ID FALLBACK
    # =========================
    def extract_order_id_fallback(self, text: str):
        match = re.search(r"\b[a-zA-Z]*\d{3,6}\b", text)
        return match.group().upper() if match else None

    # =========================
    # 🧠 ACK DETECTION
    # =========================
    def is_ack(self, text: str):
        text = text.lower().strip()
        return text in ["ok", "okay", "alright", "fine", "hmm", "right", "yes", "yeah"]

    # =========================
    # 🧠 GENERAL RESPONSE
    # =========================
    async def general_response(self, text: str):
        prompt = self.build_prompt("general_response.txt", {
            "USER_INPUT": text,
            "MEMORY": ""
        })

        response = await self.llm_call(prompt)

        if not response:
            return (
                "I’m here to assist with tracking existing orders. "
                "Could you please clarify your request?"
            )

        return response.strip()

    # =========================
    # 🎯 MAIN HANDLER (AGENTIC)
    # =========================
    async def handle(self, text: str, memory: dict, call_id: str = "unknown"):

        print(f"🧠 Input: {text}")

        # =========================
        # 🔥 ACK HANDLING
        # =========================
        if self.is_ack(text):
            return ""

        # =========================
        # 🧠 STEP 1 — ROUTE INTENT
        # =========================
        routing = await self.route_intent(text)

        intent = routing.get("intent")
        confidence = routing.get("confidence", 0)

        print(f"🧠 Intent: {intent} | Confidence: {confidence}")

        # =========================
        # 🔥 CONFIDENCE GATING
        # =========================
        if confidence < 0.6:
            intent = "general"

        # =========================
        # 🧠 STEP 2 — ORDER TRACKING
        # =========================
        if intent == "order_tracking":

            extracted = await self.extract(text)

            order_id = extracted.get("entities", {}).get("order_id")

            if not order_id:
                order_id = self.extract_order_id_fallback(text)

            if not order_id:
                return "Sure, I can help with that. Could you please provide your order ID?"

            order = self.order_service.get_order(order_id)

            if not order:
                return f"I couldn't find order {order_id}. Please check and try again."

            eta = order.get("eta", "")

            if eta.lower() == "delivered":
                eta_text = "It has already been delivered."
            elif "pending" in eta.lower():
                eta_text = "It is pending dispatch."
            else:
                eta_text = f"It is expected in {eta}."

            return (
                f"Order {order['order_id']} is {order['status']}. "
                f"It is currently at {order['location']}. "
                f"{eta_text}"
            )

        # =========================
        # 🧠 STEP 3 — GENERAL RESPONSE
        # =========================
        return await self.general_response(text)