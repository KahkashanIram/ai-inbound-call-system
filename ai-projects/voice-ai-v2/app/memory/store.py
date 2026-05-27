from app.memory.session import SessionMemory
from app.memory.structured_memory import StructuredMemory


class MemoryManager:

    def __init__(self):
        self.sessions = {}

    def get(self, session_id):

        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "history": SessionMemory(),
                "structured": StructuredMemory()
            }

        return self.sessions[session_id]

    def clear(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]