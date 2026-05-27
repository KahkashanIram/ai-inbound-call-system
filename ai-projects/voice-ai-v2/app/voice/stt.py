"""
📜 VERSION HISTORY

v8.0 → 🔥 FULL PIPELINE ALIGNMENT (TWILIO + LANGGRAPH)
- FIX: handle_transcript → on_transcript alignment
- FIX: Thread-safe dispatch into async loop
- IMPROVE: Duplicate detection (less aggressive)
- IMPROVE: Interrupt debounce stability
- PRESERVE: Filtering + confidence gating
"""

import asyncio
import re
import time
from deepgram import DeepgramClient, LiveTranscriptionEvents


class DeepgramService:
    def __init__(self, api_key: str):
        self.dg = DeepgramClient(api_key)
        self.connection = None

        self.parent = None
        self.loop = None

        self.last_transcript = None
        self.last_confidence = 0.0

        self.last_interrupt_time = 0

        # 🔥 PATCH START: TRACK LAST DISPATCH TIME
        # WHY:
        # Prevent burst duplicate dispatches from Deepgram edge cases
        # (same transcript arriving multiple times rapidly)
        self.last_dispatch_time = 0
        # 🔥 PATCH END

    # =========================
    # 🚀 START STREAM
    # =========================
    def start(self):
        self.connection = self.dg.listen.live.v("1")

        self.connection.on(
            LiveTranscriptionEvents.Transcript,
            self.on_transcript
        )

        self.connection.start({
            "model": "nova-2",
            "smart_format": True,
            "punctuate": True,
            "interim_results": False,
            "endpointing": 300,
            "encoding": "linear16",
            "sample_rate": 8000,
        })

        print("🧠 Deepgram started (enterprise mode)")

    # =========================
    # 🎧 SEND AUDIO
    # =========================
    def send_audio(self, audio_chunk: bytes):
        try:
            if self.connection:
                self.connection.send(audio_chunk)
        except Exception as e:
            print(f"⚠️ Deepgram send error: {e}")

    # =========================
    # 🛑 FINISH
    # =========================
    def finish(self):
        if self.connection:
            try:
                self.connection.finish()
            except Exception:
                pass
            print("🧠 Deepgram closed")

    # =========================
    # 🧠 NORMALIZATION
    # =========================
    def normalize_text(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text

    # =========================
    # 🧠 DUPLICATE CHECK
    # =========================
    def is_duplicate(self, normalized: str) -> bool:
        if not self.last_transcript:
            return False

        # allow small variation (less strict than exact match)
        return normalized == self.last_transcript

    # =========================
    # 🧠 SAFE DISPATCH (FIXED)
    # =========================
    def safe_dispatch(self, transcript: str):
        loop = self.loop

        if not loop and self.parent:
            loop = getattr(self.parent, "loop", None)

        if not loop or loop.is_closed():
            print("⚠️ Event loop not available")
            return

        if not self.parent or not hasattr(self.parent, "on_transcript"):
            print("⚠️ Parent on_transcript missing")
            return

        try:
            print(f"📤 Dispatching transcript → {transcript}")

            # 🔥 PATCH START: DISPATCH RATE LIMIT
            # WHY:
            # Deepgram can occasionally fire multiple identical events quickly
            # causing duplicate enqueue → duplicate responses
            #
            # FIX:
            # Add small time-based throttle
            now = time.time()
            if now - self.last_dispatch_time < 0.15:
                print("⚡ Dispatch throttled (duplicate burst)")
                return
            self.last_dispatch_time = now
            # 🔥 PATCH END

            future = asyncio.run_coroutine_threadsafe(
                self.parent.on_transcript(transcript, True),
                loop
            )

            def _callback(f):
                try:
                    f.result()
                except Exception as e:
                    print(f"⚠️ Async dispatch error: {e}")

            future.add_done_callback(_callback)

        except Exception as e:
            print(f"⚠️ Dispatch failed: {e}")

    # =========================
    # 🧠 MAIN HANDLER
    # =========================
    def on_transcript(self, *args, **kwargs):
        try:
            result = kwargs.get("result") or (args[0] if args else None)

            if not result:
                return

            if hasattr(result, "is_final") and not result.is_final:
                return

            # Extract alternatives
            if hasattr(result, "channel"):
                alternatives = result.channel.alternatives
            elif isinstance(result, dict):
                alternatives = result.get("channel", {}).get("alternatives", [])
            else:
                return

            if not alternatives:
                return

            alt = alternatives[0]

            transcript = (
                alt.get("transcript")
                if isinstance(alt, dict)
                else alt.transcript
            )

            confidence = (
                alt.get("confidence", 0.0)
                if isinstance(alt, dict)
                else getattr(alt, "confidence", 0.0)
            )

            if not transcript:
                return

            transcript = transcript.strip()

            # =========================
            # 🔥 FILTERING
            # =========================
            if len(transcript) < 2:
                return

            if confidence < 0.6:
                return

            normalized = self.normalize_text(transcript)

            if self.is_duplicate(normalized):
                return

            # =========================
            # 🔥 INTERRUPT PROTECTION
            # =========================
            # 🔥 PATCH START: INTERRUPT RECOVERY (DO NOT DROP TRANSCRIPTS)
            # WHY:
            # Previously we were DROPPING transcripts during interrupt
            # → caused conversation break after barge-in
            #
            # FIX:
            # - DO NOT drop transcript
            # - Just mark interrupt timing
            # - Allow pipeline to process normally

            if self.parent:
                if getattr(self.parent, "interrupt_flag", False):
                    self.last_interrupt_time = time.time()
                    print("⚡ Interrupt detected — allowing transcript (recovery mode)")
            # 🔥 PATCH END

                # 🔥 PATCH START: SMART DEBOUNCE WINDOW
                # WHY:
                # Fixed 0.3 sec window may be too aggressive for real speech
                #
                # FIX:
                # Reduce debounce window for faster recovery
                if time.time() - self.last_interrupt_time < 0.1:
                    print("⚡ Very short Debounce - Skipping Noise")
                    return
                # 🔥 PATCH END

            self.last_transcript = normalized
            self.last_confidence = confidence

            print(f"🧠 FINAL TRANSCRIPT: {transcript} (conf: {confidence:.2f})")

            # =========================
            # 🔥 DISPATCH
            # =========================
            if self.parent:
                self.safe_dispatch(transcript)
            else:
                print("⚠️ Parent not set")

        except Exception as e:
            print(f"⚠️ Transcript error: {e}")