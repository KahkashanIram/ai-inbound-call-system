"""
📜 VERSION HISTORY

v9.0 → 🔥 FULL PRODUCTION STABILIZATION
- FIX: Deepgram → transcript pipeline
- FIX: Queue worker (missing link)
- FIX: Barge-in (EMA + dynamic threshold + debounce + grace period)
- FIX: TTS timing + interrupt safety
- FIX: Async race conditions
- PRESERVE: Registry + streaming + observability
"""

import json
import base64
import audioop
import asyncio
import time
import re
from fastapi import WebSocket

#from app.services.agent_handler import AgentHandler
from app.voice.audio_converter import AudioConverter
from app.voice.stt import DeepgramService
from app.voice.tts import TTSService
from app.config import DEEPGRAM_API_KEY
from app.state.call_state import CallState
from app.observability.registry import active_call_registry
#----------------------------------------------------
#langGraph Imports
#--------------------------------------------------
from app.graph.graph_builder import agent_graph
from app.orchestrator.orchestrator import Orchestrator
# =========================
# 🧠 TRANSCRIPT BUFFER
# =========================
class TranscriptBuffer:
    def __init__(self):

        self.NON_BLOCKING_MODE = False  # default safe mode
       

        self.buffer = ""
        self.last_update = time.time()
        self.last_flushed = None

    def add(self, text: str):
        self.buffer += " " + text
        self.last_update = time.time()

    def should_flush(self):
        silence = time.time() - self.last_update > 1.0
        semantic = bool(re.search(r"[.!?]$", self.buffer.strip()))
        return silence or semantic

    def flush(self):
        final = self.buffer.strip()

        if not final or final == self.last_flushed:
            self.buffer = ""
            return ""

        self.last_flushed = final
        self.buffer = ""
        print(f"🧠 BUFFER FLUSH: {final}")
        return final


# =========================
# 🚀 MAIN SERVICE
# =========================
class TwilioStreamService:
    def __init__(self, llm):
        self.tts = TTSService(DEEPGRAM_API_KEY)
        self.sessions = {}
        self.llm = llm

    def get_call_state(self, call_sid: str) -> CallState:
        if call_sid not in self.sessions:
            print("🆕 NEW SESSION CREATED")
            self.sessions[call_sid] = CallState(call_sid)
        return self.sessions[call_sid]
    
"""
📜 VERSION HISTORY

v9.2 → 🔥 FINAL WRAPPER + SAFE PATCH
- ADD: handle_connection wrapper with timeout guard
- FIX: Removed duplicate websocket.accept()
- ADD: self.NON_BLOCKING_MODE
- PRESERVE: ALL existing logic (NO BREAKAGE)
"""

import json
import base64
import audioop
import asyncio
import time
import re
from fastapi import WebSocket

from app.voice.audio_converter import AudioConverter
from app.voice.stt import DeepgramService
from app.voice.tts import TTSService
from app.config import DEEPGRAM_API_KEY
from app.state.call_state import CallState
from app.observability.registry import active_call_registry

from app.graph.graph_builder import agent_graph


# =========================
# 🧠 TRANSCRIPT BUFFER
# =========================
class TranscriptBuffer:
    def __init__(self):
        self.buffer = ""
        self.last_update = time.time()
        self.last_flushed = None

    def add(self, text: str):
        self.buffer += " " + text
        self.last_update = time.time()

    def should_flush(self):
        silence = time.time() - self.last_update > 1.0
        semantic = bool(re.search(r"[.!?]$", self.buffer.strip()))
        return silence or semantic

    def flush(self):
        final = self.buffer.strip()

        if not final or final == self.last_flushed:
            self.buffer = ""
            return ""

        self.last_flushed = final
        self.buffer = ""
        print(f"🧠 BUFFER FLUSH: {final}")
        return final


# =========================
# 🚀 MAIN SERVICE
# =========================
class TwilioStreamService:
    def __init__(self, llm):
        self.tts = TTSService(DEEPGRAM_API_KEY)
        self.sessions = {}
        self.llm = llm

        # 🔥 ADD HERE
        self.orchestrator = Orchestrator(self)

        # ✅ Used in queue adaptive mode
        self.NON_BLOCKING_MODE = False

    def get_call_state(self, call_sid: str) -> CallState:
        if call_sid not in self.sessions:
            print("🆕 NEW SESSION CREATED")
            self.sessions[call_sid] = CallState(call_sid)
        return self.sessions[call_sid]

    # =========================
    # 🚀 SAFE WRAPPER (ENTRY POINT)
    # =========================
    async def handle_connection(self, websocket: WebSocket):
        """
        🔒 Wrapper Layer

        Purpose:
        - Prevent stuck calls
        - Prevent infinite loops
        - Force cleanup on crash
        """

        await websocket.accept()

        try:
            await asyncio.wait_for(
                self._handle_connection_internal(websocket),
                timeout=120  # 🔥 safety timeout
            )

        except asyncio.TimeoutError:
            print("🚨 CALL TIMEOUT — FORCE TERMINATION")

            try:
                if self.call_sid:
                    active_call_registry.end_call(self.call_sid)
            except:
                pass

        except Exception as e:
            print(f"🚨 CALL CRASH: {e}")

        finally:
            print("🧹 FORCE CLEANUP COMPLETE")

    # =========================
    # 🧠 CORE ENGINE (UNCHANGED LOGIC)
    # =========================
    async def _handle_connection_internal(self, websocket: WebSocket):

        # ❌ IMPORTANT: DO NOT accept again

        self.websocket = websocket
        self.loop = asyncio.get_running_loop()

        self.current_stream_sid = None
        self.call_sid = None

        self.is_speaking = False
        self.interrupt_flag = False

        self.queue_worker_running = False
        self.active_task = None
        self.task_queue = asyncio.Queue(maxsize=2)
        self.transcript_buffer = TranscriptBuffer()

        # 🔥 BARGE-IN STATE
        self.energy_ema = 0
        self.alpha = 0.2

        self.noise_floor = 0
        self.noise_alpha = 0.05
        self.barge_in_margin = 200

        self.tts_start_time = 0
        self.min_speak_time = 0.8

        self.barge_counter = 0
        self.barge_required_frames = 8

        deepgram = DeepgramService(DEEPGRAM_API_KEY)
        deepgram.parent = self
        deepgram.loop = self.loop

        deepgram_started = False
        greeting_sent = False

        print("🔗 Twilio WebSocket Connected")

        try:
            while True:
                message = await websocket.receive_text()
                data = json.loads(message)
                event = data.get("event")

                # =========================
                # 📞 START EVENT
                # =========================
                if event == "start":
                    stream_sid = data["start"]["streamSid"]

                    self.current_stream_sid = stream_sid
                    self.call_sid = stream_sid

                    print(f"📞 CALL STARTED: {stream_sid}")
                    active_call_registry.start_call(stream_sid)

                    if not deepgram_started:
                        deepgram.start()
                        deepgram_started = True

                    await asyncio.sleep(0.1)

                    if self.is_ws_active():
                        await self.send_silence(stream_sid)

                        if not greeting_sent:
                            greeting_sent = True
                            asyncio.create_task(self.send_greeting(stream_sid))

                # =========================
                # 🎧 MEDIA EVENT
                # =========================
                elif event == "media":
                    try:
                        payload = data["media"]["payload"]
                        mulaw_audio = base64.b64decode(payload)
                        pcm_audio = AudioConverter.mulaw_to_pcm(mulaw_audio)

                        volume = audioop.rms(pcm_audio, 2)

                        # 🔥 BARGE-IN LOGIC
                        energy = self.alpha * volume + (1 - self.alpha) * self.energy_ema
                        self.energy_ema = energy

                        if not self.is_speaking:
                            self.noise_floor = (
                                self.noise_alpha * energy +
                                (1 - self.noise_alpha) * self.noise_floor
                            )

                        threshold = self.noise_floor + self.barge_in_margin
                        after_grace = (time.time() - self.tts_start_time) > self.min_speak_time

                        if self.is_speaking and after_grace and energy > threshold:
                            self.barge_counter += 1
                        else:
                            self.barge_counter = 0

                        if self.barge_counter >= self.barge_required_frames:
                            print("🛑 BARGE-IN DETECTED")

                            self.interrupt_flag = True
                            self.is_speaking = False
                            self.barge_counter = 0

                            try:
                                await self.tts.stop()
                            except:
                                pass

                            if self.active_task:
                                self.active_task.cancel()

                            # 🔥 PATCH START: SAFE QUEUE CLEAR (NO HARD RESET)
                            while not self.task_queue.empty():
                                try:
                                    self.task_queue.get_nowait()
                                except:
                                    break
                            # 🔥 PATCH END

                            # 🔥 PATCH START: DO NOT WIPE TRANSCRIPT BUFFER
                            # WHY:
                            # Prevent losing user speech mid-interrupt
                            self.transcript_buffer.last_update = time.time()
                            # 🔥 PATCH END

                        if deepgram_started:
                            deepgram.send_audio(pcm_audio)

                        if self.transcript_buffer.should_flush():
                            text = self.transcript_buffer.flush()
                            if text:
                                await self.enqueue_task(text)

                    except Exception as e:
                        print(f"⚠️ Media error: {e}")

                # =========================
                # 🛑 STOP EVENT
                # =========================
                elif event == "stop":
                    print("📞 CALL ENDED")

                    if self.call_sid:
                        active_call_registry.end_call(self.call_sid)

                    break

        finally:
            print("🧹 CLEANING SESSION")

            if self.active_task:
                self.active_task.cancel()

            if deepgram_started:
                deepgram.finish()

    # =========================
    # 🔇 SEND SILENCE
    # =========================
    async def send_silence(self, stream_sid: str):
        if not self.is_ws_active():
            return

        silence = b'\xff' * 320

        for _ in range(8):
            try:
                payload = base64.b64encode(silence).decode()

                await self.websocket.send_json({
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {"payload": payload}
                })

                await asyncio.sleep(0.02)

            except:
                return

    # =========================
    # 👋 GREETING
    # =========================
    async def send_greeting(self, stream_sid: str):
        print("🟢 GREETING FUNCTION TRIGGERED")

        if not self.is_ws_active():
            print("❌ WS not active")
            return

        text = "Hello, this is your AI assistant. How can I help you today?"

        try:
            print("🧠 Calling TTS...")
            pcm_audio = await self.tts.synthesize(text)

            # 🔥 FALLBACK (CRITICAL)
            if not pcm_audio:
                print("⚠️ TTS FAILED → USING FALLBACK AUDIO")

                # simple beep/silence fallback to keep call alive
                pcm_audio = b'\x00' * 8000  # ~0.5 sec silence


            print(f"✅ PCM AUDIO SIZE: {len(pcm_audio)}")

            mulaw_audio = AudioConverter.pcm_to_mulaw(
                pcm_audio,
                input_rate=self.tts.sample_rate
            )

            print(f"✅ MULAW AUDIO SIZE: {len(mulaw_audio)}")

            await self.send_audio_to_twilio(mulaw_audio, stream_sid)

        except Exception as e:
            print(f"❌ send_greeting error: {e}")

    # =========================
    # 🧠 TRANSCRIPT ENTRY
    # =========================
    async def on_transcript(self, text: str, is_final: bool):
        print(f"🧠 TRANSCRIPT RECEIVED: {text}")

        if not text:
            return

        # 🔥 PATCH START: FULL INTERRUPT RECOVERY
        # WHY:
        # Ensure system resumes after barge-in
        if self.interrupt_flag:
            print("⚡ INTERRUPT RECOVERY → resuming pipeline")

            self.interrupt_flag = False

            # 🔥 Ensure queue worker is alive
            if not self.queue_worker_running:
                print("🔁 Restarting queue worker after interrupt")
                self.queue_worker_running = True
                asyncio.create_task(self.process_queue())
        # 🔥 PATCH END

        if is_final:
            print(f"🧠 FINAL TRANSCRIPT: {text}")
            await self.orchestrator.handle_transcript(
                text
            )
        else:
            self.transcript_buffer.add(text)

    # =========================
    # 🔒 QUEUE
    # =========================
    async def enqueue_task(self, text: str):
        """
        🔥 QUEUE HANDLER (STABILIZED)

        Fixes:
        - Skips low-value inputs (ok, hmm, etc.)
        - Prevents queue pollution
        - Adds debug visibility
        """

        if not text:
            return

        clean_text = text.lower().strip()

        # =========================
        # 🔥 FILTER LOW-VALUE INPUTS
        # =========================
        if clean_text in ["ok", "okay", "hmm", "yes", "right"]:
            print(f"⚡ SKIPPED LOW VALUE INPUT: {text}")
            return

        # =========================
        # 🔥 QUEUE FULL PROTECTION
        # =========================
        if self.task_queue.full():
            print("⚠️ QUEUE FULL — DROPPING INPUT")
            return

        # =========================
        # 📥 ENQUEUE
        # =========================
        print(f"📥 ENQUEUE: {text}")
        await self.task_queue.put(text)

        # =========================
        # 🚀 START WORKER IF NEEDED
        # =========================
        if not self.queue_worker_running:
            print("⚙️ STARTING QUEUE WORKER")
            self.queue_worker_running = True
            asyncio.create_task(self.process_queue())
    #async def process_queue(self):
        #print("⚙️ QUEUE WORKER STARTED")

        #while not self.task_queue.empty():
            #text = await self.task_queue.get()

            #print(f"⚙️ PROCESSING: {text}")

            #self.active_task = asyncio.create_task(
                #self.process_final_transcript(text)
            #)

            #await self.active_task

        #self.queue_worker_running = False
    # =========================
    # 🔒 QUEUE WORKER (UPDATED)
    # =========================
    async def process_queue(self):
        print("⚙️ QUEUE WORKER STARTED")

        total_calls = active_call_registry.total_calls

        NON_BLOCKING_MODE = (
            self.NON_BLOCKING_MODE or
            total_calls > 30
        )

        if NON_BLOCKING_MODE:
            print(f"⚡ NON-BLOCKING MODE ENABLED | Active Calls: {total_calls}")

        try:
            while not self.task_queue.empty():
                text = await self.task_queue.get()

                print(f"⚙️ PROCESSING: {text}")

                task = asyncio.create_task(
                    self.process_final_transcript(text)
                )

                self.active_task = task

                if not NON_BLOCKING_MODE:
                    try:
                        await task
                    except asyncio.CancelledError:
                        print("⚠️ Task cancelled (barge-in)")

                        # 🔥 PATCH START: DO NOT KILL WORKER
                        continue
                        # 🔥 PATCH END
                else:
                    task.add_done_callback(
                        lambda t: print("✅ Task completed (non-blocking)")
                    )

        finally:
            # 🔥 PATCH START: SELF-HEALING WORKER
            self.queue_worker_running = False

            if not self.task_queue.empty():
                self.queue_worker_running = True
                asyncio.create_task(self.process_queue())
            # 🔥 PATCH END
    # =========================
    # 🤖 AGENT PIPELINE
    # =========================
    async def process_final_transcript(self, transcript: str):

        try:
            call_state = self.get_call_state(self.call_sid)
            await call_state.set_user_input(transcript)

            graph_result = await agent_graph.ainvoke({
                "input": transcript,
                "user_input": transcript,
                "call_id": self.call_sid,
                "memory": call_state.get_memory()
            })

            response = (
                graph_result.get("response")
                or graph_result.get("output")
                or "I didn't catch that. Could you repeat?"
            )

        # 🔥 PATCH START: SAFE CANCEL EXIT
        except asyncio.CancelledError:
            print("⚠️ PROCESS CANCELLED (SAFE EXIT)")
            return
        # 🔥 PATCH END

        except Exception:
            response = "Sorry, something went wrong."

        pcm_audio = await self.tts.synthesize(response)

        if not pcm_audio:
            return

        mulaw_audio = AudioConverter.pcm_to_mulaw(
            pcm_audio,
            input_rate=self.tts.sample_rate
        )

        await self.send_audio_to_twilio(mulaw_audio, self.current_stream_sid)
    # =========================
    # 🔊 AUDIO OUT
    # =========================
    async def send_audio_to_twilio(self, mulaw_audio: bytes, stream_sid: str):
        print("🔊 START STREAMING TO TWILIO")

        self.is_speaking = True
        self.tts_start_time = time.time()
        self.interrupt_flag = False

        chunk_size = 160

        for i in range(0, len(mulaw_audio), chunk_size):

            if self.interrupt_flag or not self.is_ws_active():
                self.is_speaking = False
                return

            chunk = mulaw_audio[i:i + chunk_size]
            payload = base64.b64encode(chunk).decode()

            await self.websocket.send_json({
                "event": "media",
                "streamSid": stream_sid,
                "media": {"payload": payload}
            })

            await asyncio.sleep(0.02)

        self.is_speaking = False

    # =========================
    def is_ws_active(self):
        try:
            return self.websocket.client_state.name == "CONNECTED"
        except:
            return False