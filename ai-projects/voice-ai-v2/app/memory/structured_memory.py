class StructuredMemory:
    def __init__(self):
        self.data = {
            "active_flow": None,
            "entities": {
                "order_id": None
            },
            "awaiting": None
        }

    def update(self, **kwargs):
        for key, value in kwargs.items():
            self.data[key] = value

    def get(self):
        return self.data