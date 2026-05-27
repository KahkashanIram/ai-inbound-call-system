"""
📜 VERSION HISTORY

v3.3 → 🚀 ENTERPRISE TTS (CONCURRENCY CONTROL ADDED)
- ADD: semaphore-based concurrency control
- ADD: overload protection (skip TTS if busy)
- KEEP: interrupt-safe playback
- KEEP: Deepgram integration
"""

import httpx
import logging
import time  # 🔥 PATCH: needed for timing control

from app.core.concurrency import run_controlled, tts_semaphore, OverloadError

logger = logging.getLogger(__name__)


class TTSService:
    def __init__(self, api_key: str):
        self.api_key = api_key

        # 🔥 BASE CONFIG
        self.base_url = "https://api.deepgram.com/v1/speak"
        self.model = "aura-asteria-en"
        self.encoding = "linear16"
        self.sample_rate = 8000

        # ✅ FINAL URL (PRECOMPUTED)
        self.url = (
            f"{self.base_url}"
            f"?model={self.model}"
            f"&encoding={self.encoding}"
            f"&sample_rate={self.sample_rate}"
        )

        # ✅ HEADERS (PRECOMPUTED)
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }

        # 🔥 SPEAKING STATE
        self.is_speaking = False

        # 🔥 PATCH START: REQUEST TRACKING
        # WHY:
        # Prevent overlapping responses from older requests
        # (race condition: slow TTS returns after new request starts)
        self.request_id = 0
        # 🔥 PATCH END

    # =========================
    # 🔊 INTERNAL SYNTHESIZE (ORIGINAL LOGIC)
    # =========================
    async def _synthesize_internal(self, text: str) -> bytes:

        if not text:
            return b""

        # 🔥 PATCH START: TRACK CURRENT REQUEST
        # WHY:
        # Each TTS call gets unique ID → helps ignore stale responses
        self.request_id += 1
        current_request_id = self.request_id
        # 🔥 PATCH END

        self.is_speaking = True

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.post(
                    self.url,
                    headers=self.headers,
                    json={"text": text}
                )

                response.raise_for_status()

                # 🔴 INTERRUPT CHECK
                if not self.is_speaking:
                    logger.info("🛑 TTS interrupted before playback")
                    return b""

                # 🔥 PATCH START: STALE RESPONSE PROTECTION
                # WHY:
                # If a newer request started while this one was running,
                # this response is outdated → must not be played
                if current_request_id != self.request_id:
                    logger.info("⚡ Skipping stale TTS response")
                    return b""
                # 🔥 PATCH END

                if not response.content:
                    logger.warning("⚠️ TTS returned empty audio")
                    return b""

                return response.content

        except httpx.ConnectTimeout:
            logger.warning("⚠️ TTS Connect Timeout")
            return b""

        except httpx.ReadTimeout:
            logger.warning("⚠️ TTS Read Timeout")
            return b""

        except httpx.HTTPStatusError as e:
            logger.error(f"⚠️ TTS HTTP Error: {e.response.text}")
            return b""

        except Exception as e:
            logger.exception(f"⚠️ TTS Unexpected Error: {e}")
            return b""

        finally:
            self.is_speaking = False

    # =========================
    # 🔊 ENTERPRISE SYNTHESIZE (CONTROLLED)
    # =========================
    async def synthesize(self, text: str) -> bytes:
        """
        🔥 Enterprise-safe TTS:
        - concurrency controlled
        - overload protected
        - interrupt safe
        """

        async def _call():
            return await self._synthesize_internal(text)

        try:
            return await run_controlled(
                semaphore=tts_semaphore,
                coro=_call,
                timeout=8.0,
                task_name="TTS"
            )

        except OverloadError:
            logger.warning("🚨 TTS OVERLOAD → skipping audio")
            return b""

        except Exception as e:
            logger.exception(f"❌ TTS CONTROL ERROR: {e}")
            return b""

    # =========================
    # 🛑 HARD STOP (BARGE-IN)
    # =========================
    async def stop(self):
        """
        🔥 Immediately stop TTS
        """

        if self.is_speaking:
            logger.info("🛑 TTS STOP CALLED")

        # 🔥 PATCH START: HARD INVALIDATE ALL REQUESTS
        # WHY:
        # Ensure ANY in-flight request becomes stale immediately
        # (prevents delayed audio after interrupt)
        self.request_id += 1
        # 🔥 PATCH END

        self.is_speaking = False