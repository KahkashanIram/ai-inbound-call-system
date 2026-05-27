from fastapi import APIRouter
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant

import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()


@router.get("/token")
def generate_token():

    identity = "user"

    token = AccessToken(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_API_KEY"),
        os.getenv("TWILIO_API_SECRET"),
        identity=identity
    )

    voice_grant = VoiceGrant(
        outgoing_application_sid=os.getenv("TWILIO_APP_SID"),
        incoming_allow=True
    )

    token.add_grant(voice_grant)

    return {"token": token.to_jwt()}