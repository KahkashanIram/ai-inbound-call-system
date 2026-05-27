# app/services/llm_service.py

import os
import asyncio
import time
from openai import AsyncOpenAI

from app.core.concurrency import (
    run_controlled,
    llm_semaphore,
    OverloadError
)

from app.observability.tracer import trace_manager


class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )

        # 🔥 Model config (can be dynamic later)
        self.model = "gpt-4o-mini"

        # 🔥 Circuit breaker state
        self.failures = 0
        self.disabled_until = 0

    # =========================
    # 🚀 MAIN GENERATE FUNCTION
    # =========================
    async def generate(self, prompt: str, call_id: str = None) -> str:

        async def _call():
            return await self._execute_llm(prompt, call_id)

        try:
            return await run_controlled(
                semaphore=llm_semaphore,
                coro=_call,
                timeout=2.5,
                task_name="LLM"
            )

        except OverloadError:
            print("🚨 LLM OVERLOAD → fallback response")
            return "I'm handling many requests right now. Please try again."

        except Exception as e:
            print(f"❌ LLM SYSTEM ERROR: {e}")
            return "I'm experiencing a temporary issue."

    # =========================
    # 🧠 CORE EXECUTION
    # =========================
    async def _execute_llm(self, prompt: str, call_id: str = None) -> str:

        # 🔥 Circuit breaker check
        if time.time() < self.disabled_until:
            print("🚨 LLM CIRCUIT BREAKER ACTIVE")
            raise Exception("LLM temporarily disabled")

        start_time = time.time()

        for attempt in range(3):  # 🔁 retries
            try:
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.2
                    ),
                    timeout=2.0
                )

                content = response.choices[0].message.content.strip()

                # 🔥 reset failures on success
                self.failures = 0

                # 📊 observability
                if call_id:
                    trace_manager.log(
                        call_id=call_id,
                        node="llm_call",
                        output_data={
                            "latency": round(time.time() - start_time, 3),
                            "attempt": attempt + 1
                        }
                    )

                return content

            except asyncio.TimeoutError:
                print(f"⏱️ LLM TIMEOUT (attempt {attempt+1})")

            except Exception as e:
                print(f"⚠️ LLM ERROR (attempt {attempt+1}): {e}")

            # 🔁 backoff
            await asyncio.sleep(0.2 * (attempt + 1))
            self.failures += 1

        # 🚨 Circuit breaker activation
        if self.failures >= 5:
            self.disabled_until = time.time() + 10
            print("🚨 LLM CIRCUIT BREAKER ACTIVATED")

        raise Exception("LLM failed after retries")