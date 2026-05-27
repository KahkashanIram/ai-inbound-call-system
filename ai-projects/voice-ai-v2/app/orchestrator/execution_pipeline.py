class ExecutionPipeline:

    def __init__(self, parent):
        self.parent = parent

    async def execute(
        self,
        transcript: str
    ):
        """
        Current:
            transcript -> queue

        Future:
            transcript
              ↓
            cognition
              ↓
            memory
              ↓
            graph
        """

        await self.parent.enqueue_task(
            transcript
        )