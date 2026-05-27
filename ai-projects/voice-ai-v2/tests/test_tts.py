import asyncio
from dotenv import load_dotenv
load_dotenv()

from app.services.tts_service import TTSService
from app.config import DEEPGRAM_API_KEY


async def main():
    tts = TTSService(api_key=DEEPGRAM_API_KEY)

    texts = [
        "Hello, welcome to ABC Dispatch Department.",
        "Your order has been successfully dispatched.",
        "Please hold while I check your request."
    ]

    for i, text in enumerate(texts):
        print(f"\n🔊 Generating audio for: {text}")

        audio = await tts.synthesize(text)

        print(f"📦 Audio length: {len(audio)} bytes")

        with open(f"output_{i}.raw", "wb") as f:
            f.write(audio)

        print(f"✅ Saved: output_{i}.raw")


if __name__ == "__main__":
    asyncio.run(main())