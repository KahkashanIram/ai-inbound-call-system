class SessionMemory:
    def __init__(self, max_turns=6):
        self.history = []
        self.max_turns = max_turns

    def add(self, user, assistant):
        self.history.append({
            "user": user,
            "assistant": assistant
        })

        if len(self.history) > self.max_turns:
            self.history.pop(0)

    def get(self):
        return self.history