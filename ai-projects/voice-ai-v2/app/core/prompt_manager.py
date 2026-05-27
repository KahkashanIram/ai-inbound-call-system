# app/core/prompt_manager.py

import threading
from pathlib import Path
from typing import Dict


class PromptManager:
    """
    🧠 Enterprise Prompt Engine

    Features:
    - Zero runtime disk I/O
    - O(1) lookup
    - Thread-safe reads
    - Hot reload support
    - Validation layer
    - Future-ready (versioning, remote config)
    """

    def __init__(self, base_path: str = "app/prompts"):
        self.base_path = Path(base_path)

        # 🔒 Thread-safe storage
        self._lock = threading.RLock()

        # 🔥 In-memory prompt store
        self._prompts: Dict[str, str] = {}

        # 🚀 Load once at startup
        self._load_all()

    # =========================
    # 🚀 LOAD PROMPTS (STARTUP)
    # =========================
    def _load_all(self):
        if not self.base_path.exists():
            raise FileNotFoundError(f"Prompt directory not found: {self.base_path}")

        loaded = {}

        for file in self.base_path.glob("*.txt"):
            try:
                content = file.read_text(encoding="utf-8").strip()

                if not content:
                    print(f"⚠️ Empty prompt: {file.name}")
                    continue

                loaded[file.name] = content

            except Exception as e:
                print(f"❌ Failed to load {file.name}: {e}")

        with self._lock:
            self._prompts = loaded

        print(f"✅ PromptManager loaded {len(self._prompts)} prompts")

    # =========================
    # ⚡ FAST GET (O(1))
    # =========================
    def get(self, name: str) -> str:
        """
        🔥 Ultra-fast prompt retrieval
        No locking for read (safe due to atomic dict swap)
        """
        prompt = self._prompts.get(name)

        if prompt is None:
            print(f"⚠️ Prompt not found: {name}")
            return ""

        return prompt

    # =========================
    # 🔄 HOT RELOAD (NON-BLOCKING)
    # =========================
    def reload(self):
        """
        🔥 Reload prompts without restarting server
        Atomic swap → zero downtime
        """
        print("🔄 Reloading prompts...")

        try:
            self._load_all()
            print("✅ Prompts reloaded successfully")

        except Exception as e:
            print(f"❌ Reload failed: {e}")

    # =========================
    # 🧪 VALIDATION
    # =========================
    def validate(self):
        """
        Validate prompt integrity
        """
        issues = []

        for name, content in self._prompts.items():
            if not content.strip():
                issues.append(name)

        if issues:
            print(f"⚠️ Invalid prompts: {issues}")
        else:
            print("✅ All prompts valid")

    # =========================
    # 📊 DEBUG / STATS
    # =========================
    def stats(self):
        return {
            "total_prompts": len(self._prompts),
            "prompt_names": list(self._prompts.keys())
        }


# 🔥 GLOBAL SINGLETON (IMPORTANT)
prompt_manager = PromptManager()