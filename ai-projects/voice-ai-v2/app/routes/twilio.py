"""
📜 VERSION: v3.0 (AI-FIRST FINAL)

🔥 ARCHITECTURE:
- NO TwiML greeting
- Twilio acts as transport only
- AI (WebSocket) handles greeting + conversation
- Uses <Connect> for bidirectional streaming
"""

from fastapi import APIRouter, Request
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Connect

router = APIRouter()


@router.post("/twilio/voice")
async def twilio_voice(request: Request):

    print("📞 Twilio webhook HIT")

    response = VoiceResponse()

    # ✅ ONLY CONNECT STREAM (NO GREETING)
    connect = Connect()
    connect.stream(
        url="wss://wasteful-sky-controvertibly.ngrok-free.dev/ws/twilio-stream"
    )
    response.append(connect)

    # 🔒 Keep call alive
    response.pause(length=60)

    return Response(content=str(response), media_type="application/xml")