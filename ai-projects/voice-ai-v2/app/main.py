from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

# =========================
# 📡 ROUTERS
# =========================
from app.routes import twilio
from app.routes import token

# =========================
# 🧠 SERVICES
# =========================

# ✅ MOVED FROM services → voice
from app.voice.stream import TwilioStreamService

# keep existing
from app.services.llm_service import LLMService


# =========================
# 🚀 APP INIT
# =========================
app = FastAPI()


# =========================
# 🧠 CORE DEPENDENCIES
# =========================

# One global LLM instance
llm = LLMService()

# Twilio streaming service
twilio_stream_service = TwilioStreamService(llm)


# =========================
# 📡 ROUTERS
# =========================
app.include_router(twilio.router)
app.include_router(token.router)


# =========================
# 📁 STATIC FILES
# =========================
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# =========================
# 🏠 ROOT
# =========================
@app.get("/")
def root():
    return {
        "message": "Voice AI Server Running"
    }


# =========================
# 🔊 TWILIO WS
# =========================
@app.websocket("/ws/twilio-stream")
async def twilio_stream(websocket: WebSocket):
    await twilio_stream_service.handle_connection(
        websocket
    )