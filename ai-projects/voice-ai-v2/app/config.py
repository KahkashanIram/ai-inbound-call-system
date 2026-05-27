# =========================================================
# 🔐 CONFIG FILE (CENTRALIZED ENV MANAGEMENT)
# =========================================================

import os
from dotenv import load_dotenv

# =========================================================
# ✅ STEP 1: LOAD ENV FILE
# =========================================================
load_dotenv()


# =========================================================
# 🔑 API KEYS
# =========================================================

# 🎧🔑 Deepgram API KEY (STT Layer)
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# 🧠🔑 OpenAI API KEY (Agent Layer - LLM)   🔥 NEW
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# =========================================================
# ⚠️ STEP 2: SAFETY CHECK (CRITICAL FOR PRODUCTION)
# =========================================================

if not DEEPGRAM_API_KEY:
    raise ValueError("❌ DEEPGRAM_API_KEY is missing in .env")

if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY is missing in .env")  # 🔥 NEW


# =========================================================
# 🔍 STEP 3: DEBUG LOG (TEMP - REMOVE LATER)
# =========================================================

print("✅ CONFIG LOADED")

if DEEPGRAM_API_KEY:
    print("🎧 Deepgram Key:", DEEPGRAM_API_KEY[:8], "...")

if OPENAI_API_KEY:
    print("🧠 OpenAI Key:", OPENAI_API_KEY[:8], "...")  # 🔥 NEW