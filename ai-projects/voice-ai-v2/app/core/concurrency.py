# app/core/concurrency.py

import asyncio
import time
from typing import Callable, Any


# =========================
# ⚙️ CONFIG (TUNEABLE)
# =========================
MAX_LLM_CONCURRENT = 20
MAX_TTS_CONCURRENT = 30
QUEUE_TIMEOUT = 0.05  # 🔥 reject fast if overloaded


# =========================
# 🔥 SEMAPHORES
# =========================
llm_semaphore = asyncio.Semaphore(MAX_LLM_CONCURRENT)
tts_semaphore = asyncio.Semaphore(MAX_TTS_CONCURRENT)


# =========================
# 🚨 OVERLOAD PROTECTION
# =========================
class OverloadError(Exception):
    pass


# =========================
# 🧠 NON-BLOCKING ACQUIRE
# =========================
async def try_acquire(semaphore: asyncio.Semaphore):

    start = time.time()

    while True:
        if semaphore.locked():
            if time.time() - start > QUEUE_TIMEOUT:
                raise OverloadError("System overloaded")
            await asyncio.sleep(0.001)
        else:
            await semaphore.acquire()
            return


# =========================
# 🔥 SAFE EXECUTOR (ENTERPRISE)
# =========================
async def run_controlled(
    semaphore: asyncio.Semaphore,
    coro: Callable[[], Any],
    timeout: float = 3.0,
    task_name: str = "task"
):
    """
    🔥 Elite execution wrapper:
    - Non-blocking acquire
    - Timeout protected
    - Overload rejection
    - Auto release
    """

    try:
        await try_acquire(semaphore)

        try:
            return await asyncio.wait_for(coro(), timeout=timeout)

        finally:
            semaphore.release()

    except OverloadError:
        # 🔥 immediate fallback (no queue buildup)
        print(f"🚨 OVERLOAD REJECTED: {task_name}")
        raise

    except asyncio.TimeoutError:
        print(f"⏱️ TIMEOUT: {task_name}")
        raise

    except Exception as e:
        print(f"❌ EXECUTION ERROR ({task_name}): {e}")
        raise